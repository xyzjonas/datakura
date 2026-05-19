from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q, QuerySet

from apps.warehouse.core.schemas.packaging import BatchCreateOrUpdateSchema, BatchSchema
from apps.warehouse.core.services.barcode_generator import barcode_generator_service
from apps.warehouse.core.transformation import barcode_orm_to_schema
from apps.warehouse.models.barcode import BarcodeType, Barcode
from apps.warehouse.models.warehouse import Batch


class BatchesService:
    @staticmethod
    def get_batches(search_term: str | None = None) -> QuerySet[Batch]:
        qs = Batch.objects.all()
        ct = ContentType.objects.get_for_model(Batch)

        if search_term:
            matching_ids = Barcode.objects.filter(
                content_type=ct,
                code__icontains=search_term,
            ).values_list("object_id", flat=True)
            qs = qs.filter(
                Q(description__icontains=search_term) | Q(id__in=matching_ids)
            ).distinct()
        return qs.order_by("-created")

    @staticmethod
    def batch_orm_to_schema(batch: Batch) -> BatchSchema:
        primary_barcode = batch.get_primary_barcode()
        return BatchSchema(
            id=batch.pk,
            created=batch.created,
            changed=batch.changed,
            primary_barcode=barcode_orm_to_schema(primary_barcode)
            if primary_barcode
            else None,
            description=batch.description,
        )

    @staticmethod
    @transaction.atomic
    def create_batch(params: BatchCreateOrUpdateSchema) -> BatchSchema:
        batch = Batch.objects.create(description=params.description)

        # Handle barcode
        barcode_code = params.barcode
        if params.auto_generate_barcode or not barcode_code:
            barcode_code = barcode_generator_service.generate(
                BarcodeType.CUSTOM, prefix="BAT", length=12
            )

        if barcode_code:
            batch.attach_barcode(barcode_code, BarcodeType.CUSTOM, is_primary=True)

        return BatchesService.batch_orm_to_schema(batch)

    @staticmethod
    @transaction.atomic
    def update_batch(batch_id: int, params: BatchCreateOrUpdateSchema) -> BatchSchema:
        batch = Batch.objects.get(id=batch_id)

        batch.description = params.description
        batch.save(update_fields=["description", "changed"])

        # Handle barcode update if provided
        if params.barcode:
            current_primary = batch.get_primary_barcode()
            if not current_primary or current_primary.code != params.barcode:
                batch.attach_barcode(
                    params.barcode, BarcodeType.CUSTOM, is_primary=True
                )

        return BatchesService.batch_orm_to_schema(batch)

    @staticmethod
    @transaction.atomic
    def delete_batch(batch_id: int) -> None:
        Batch.objects.get(id=batch_id).delete()


batches_service = BatchesService()
