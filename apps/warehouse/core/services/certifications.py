from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Min, Q, QuerySet, Sum

from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.core.schemas.certification import (
    AvailableCertificationSchema,
    CertificationAttachSchema,
    CertificationFormSchema,
)
from apps.warehouse.core.schemas.packaging import BatchCreateOrUpdateSchema
from apps.warehouse.core.services.batches import batches_service
from apps.warehouse.core.transformation import (
    batch_primary_barcode,
    certification_attachment_to_schema,
)
from apps.warehouse.models.orders import InboundOrderItem
from apps.warehouse.models.warehouse import Batch, Certification, WarehouseItem


def _clean_code(code: str) -> str:
    code = code.strip()
    if not code:
        raise WarehouseItemBadRequestError("Certification code must not be empty.")
    return code


class CertificationsService:
    @staticmethod
    def get_certifications(search_term: str | None = None) -> QuerySet[Certification]:
        qs = Certification.objects.prefetch_related("batches")
        if search_term:
            qs = qs.filter(
                Q(code__icontains=search_term) | Q(description__icontains=search_term)
            )
        return qs.order_by("-created")

    @staticmethod
    def get_certification(certification_id: int) -> Certification:
        return Certification.objects.get(pk=certification_id)

    @staticmethod
    def create_certification(
        params: CertificationFormSchema, attachment: UploadedFile | None = None
    ) -> Certification:
        return Certification.objects.create(
            code=_clean_code(params.code),
            description=params.description,
            attachment=attachment,
        )

    @staticmethod
    def update_certification(
        certification_id: int,
        params: CertificationFormSchema,
        attachment: UploadedFile | None = None,
    ) -> Certification:
        certification = Certification.objects.get(pk=certification_id)
        certification.code = _clean_code(params.code)
        certification.description = params.description
        if attachment is not None:
            if certification.attachment:
                certification.attachment.delete(save=False)
            certification.attachment = attachment
        certification.save()
        return certification

    @staticmethod
    @transaction.atomic
    def delete_certification(certification_id: int) -> None:
        certification = Certification.objects.get(pk=certification_id)
        if WarehouseItem.objects.filter(batch__certification=certification).exists():
            raise WarehouseItemBadRequestError(
                "Certification covers goods in the warehouse and cannot be deleted."
            )
        batch_ids = list(certification.batches.values_list("pk", flat=True))
        if certification.attachment:
            certification.attachment.delete(save=False)
        certification.delete()
        # Unused batches created for certified order rows go away with it.
        Batch.objects.filter(
            pk__in=batch_ids,
            inventory__isnull=True,
            outbound_order_items__isnull=True,
        ).delete()

    # ── inbound order item binding ──────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def attach_to_inbound_item(
        cls,
        item: InboundOrderItem,
        params: CertificationAttachSchema,
        attachment: UploadedFile | None = None,
    ) -> InboundOrderItem:
        """
        Link a certification to an inbound order row.

        A dedicated batch is created for the row and pointed at the
        certification, so the delivered goods stay traceable.
        """
        if not item.requires_certification:
            raise WarehouseItemBadRequestError(
                "Order item is not flagged as requiring certification."
            )

        if params.certification_id is not None:
            certification = Certification.objects.get(pk=params.certification_id)
        else:
            if not params.code:
                raise WarehouseItemBadRequestError(
                    "Certification code is required when creating a new certification."
                )
            if attachment is None:
                raise WarehouseItemBadRequestError(
                    "Certification attachment is required."
                )
            certification = cls.create_certification(
                CertificationFormSchema(
                    code=params.code, description=params.description
                ),
                attachment,
            )

        cls.release_batch(item)

        batch_schema = batches_service.create_batch(
            BatchCreateOrUpdateSchema(
                description=f"{certification.code} / {item.order.code}",
                auto_generate_barcode=True,
            )
        )
        batch = Batch.objects.get(pk=batch_schema.id)
        batch.certification = certification
        batch.save(update_fields=["certification", "changed"])

        item.certification = certification
        item.batch = batch
        item.save(update_fields=["certification", "batch", "changed"])
        return item

    @classmethod
    @transaction.atomic
    def detach_from_inbound_item(cls, item: InboundOrderItem) -> InboundOrderItem:
        cls.release_batch(item)
        item.certification = None
        item.save(update_fields=["certification", "changed"])
        return item

    @staticmethod
    def release_batch(item: InboundOrderItem) -> None:
        """Drop the row's current batch (deleting it if nothing else uses it)."""
        old_batch = item.batch
        if old_batch is None:
            return
        item.batch = None
        item.save(update_fields=["batch", "changed"])
        if not (
            old_batch.inbound_order_items.exists()
            or old_batch.inventory.exists()
            or old_batch.outbound_order_items.exists()
        ):
            old_batch.delete()

    @staticmethod
    def get_batch_barcode_for_inbound_item(item: InboundOrderItem) -> str | None:
        return batch_primary_barcode(item.batch) if item.batch else None

    # ── outbound picker ─────────────────────────────────────────────────────

    @staticmethod
    def get_available_for_product(
        product_code: str,
    ) -> list[AvailableCertificationSchema]:
        """Certified goods of `product_code` that can be picked right now."""
        rows = (
            WarehouseItem.available.filter(
                stock_product__code=product_code,
                batch__certification__isnull=False,
            )
            .values("batch_id", "batch__certification_id")
            .annotate(total=Sum("amount"))
        )

        per_cert: dict[int, list[tuple[int, Decimal]]] = defaultdict(list)
        for row in rows:
            if row["total"] and row["total"] > 0:
                per_cert[row["batch__certification_id"]].append(
                    (row["batch_id"], row["total"])
                )
        if not per_cert:
            return []

        ordered = dict(
            InboundOrderItem.objects.filter(certification_id__in=per_cert)
            .values("certification_id")
            .annotate(first=Min("order__created"))
            .values_list("certification_id", "first")
        )

        result: list[AvailableCertificationSchema] = []
        for cert in Certification.objects.filter(pk__in=per_cert):
            batches = per_cert[cert.pk]
            best_batch_id = max(batches, key=lambda b: b[1])[0]
            barcode = batch_primary_barcode(Batch.objects.get(pk=best_batch_id))
            if barcode is None:
                continue
            result.append(
                AvailableCertificationSchema(
                    id=cert.pk,
                    code=cert.code,
                    description=cert.description,
                    attachment=certification_attachment_to_schema(cert),
                    ordered_date=ordered.get(cert.pk) or cert.created,
                    amount=float(sum(total for _, total in batches)),
                    batch_code=barcode,
                )
            )
        result.sort(key=lambda r: r.ordered_date, reverse=True)
        return result


certifications_service = CertificationsService()
