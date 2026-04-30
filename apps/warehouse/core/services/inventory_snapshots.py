from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.warehouse.core.exceptions import WarehouseGenericError
from apps.warehouse.core.schemas.analytics import (
    InventorySnapshotCurrencyTotal,
    InventorySnapshotDetailSchema,
    InventorySnapshotLineSchema,
    InventorySnapshotSummarySchema,
    LatestInventoryValueSchema,
)
from apps.warehouse.models.warehouse import (
    InventorySnapshot,
    InventorySnapshotLine,
    InventorySnapshotTriggerSource,
    WarehouseItem,
)

PRICE_SCALE = Decimal("0.0001")


class InventorySnapshotService:
    @staticmethod
    def _quantize(value: Decimal) -> Decimal:
        return value.quantize(PRICE_SCALE, rounding=ROUND_HALF_UP)

    @classmethod
    def _serialize_totals(cls, totals: dict[str, Decimal]) -> dict[str, str]:
        return {
            currency: format(cls._quantize(value), "f")
            for currency, value in sorted(totals.items())
        }

    @staticmethod
    def _deserialize_totals(
        totals_by_currency: dict[str, str],
    ) -> list[InventorySnapshotCurrencyTotal]:
        return [
            InventorySnapshotCurrencyTotal(currency=currency, value=Decimal(value))
            for currency, value in sorted(totals_by_currency.items())
        ]

    @staticmethod
    def _resolve_bucket_key(cadence: str | None, captured_at: datetime) -> str | None:
        if cadence is None:
            return None

        if cadence == "daily":
            return captured_at.astimezone(timezone.get_current_timezone()).strftime(
                "%Y-%m-%d"
            )
        if cadence == "monthly":
            return captured_at.astimezone(timezone.get_current_timezone()).strftime(
                "%Y-%m"
            )

        return None

    @classmethod
    def _to_summary_schema(
        cls,
        snapshot: InventorySnapshot,
    ) -> InventorySnapshotSummarySchema:
        return InventorySnapshotSummarySchema(
            id=snapshot.pk,
            created=snapshot.created,
            changed=snapshot.changed,
            captured_at=snapshot.captured_at,
            trigger_source=snapshot.trigger_source,
            cadence=snapshot.cadence,
            bucket_key=snapshot.bucket_key,
            line_count=snapshot.line_count,
            purchase_totals=cls._deserialize_totals(
                snapshot.purchase_totals_by_currency
            ),
            receipt_totals=cls._deserialize_totals(snapshot.receipt_totals_by_currency),
            receipt_unpriced_line_count=snapshot.receipt_unpriced_line_count,
            receipt_complete=snapshot.receipt_unpriced_line_count == 0,
        )

    @classmethod
    def _to_detail_schema(
        cls,
        snapshot: InventorySnapshot,
    ) -> InventorySnapshotDetailSchema:
        lines = [
            InventorySnapshotLineSchema(
                id=line.pk,
                warehouse_item_id=line.warehouse_item_id,
                warehouse_item_id_at_snapshot=line.warehouse_item_id_at_snapshot,
                product_code=line.product_code,
                product_name=line.product_name,
                location_code=line.location_code,
                quantity=line.quantity,
                unit_of_measure=line.unit_of_measure,
                tracking_level=line.tracking_level,
                purchase_currency=line.purchase_currency,
                purchase_unit_price=line.purchase_unit_price,
                purchase_line_value=line.purchase_line_value,
                receipt_currency=line.receipt_currency,
                receipt_unit_price=line.receipt_unit_price,
                receipt_line_value=line.receipt_line_value,
                receipt_price_available=line.receipt_price_available,
                receipt_price_fallback_reason=line.receipt_price_fallback_reason,
            )
            for line in snapshot.lines.all()
        ]

        summary = cls._to_summary_schema(snapshot)
        return InventorySnapshotDetailSchema(**summary.model_dump(), lines=lines)

    @staticmethod
    def list_snapshots_queryset():
        return InventorySnapshot.objects.all()

    @classmethod
    def get_snapshot(cls, snapshot_id: int) -> InventorySnapshotDetailSchema:
        snapshot = InventorySnapshot.objects.prefetch_related("lines").get(
            pk=snapshot_id
        )
        return cls._to_detail_schema(snapshot)

    @classmethod
    def get_latest_snapshot_value(cls) -> LatestInventoryValueSchema:
        snapshot = InventorySnapshot.objects.first()
        if snapshot is None:
            return LatestInventoryValueSchema(snapshot=None)
        return LatestInventoryValueSchema(snapshot=cls._to_summary_schema(snapshot))

    @classmethod
    def create_snapshot(
        cls,
        *,
        trigger_source: str = InventorySnapshotTriggerSource.MANUAL,
        cadence: str | None = None,
        bucket_key: str | None = None,
        force: bool = False,
        captured_at: datetime | None = None,
    ) -> InventorySnapshotDetailSchema:
        captured_at = captured_at or timezone.now()
        derived_bucket_key = bucket_key or cls._resolve_bucket_key(cadence, captured_at)

        if trigger_source == InventorySnapshotTriggerSource.SCHEDULED:
            if cadence is None and derived_bucket_key is None:
                raise WarehouseGenericError(
                    "Scheduled snapshots require a cadence or explicit bucket key."
                )

            if cadence and derived_bucket_key is None:
                raise WarehouseGenericError(
                    "Unsupported cadence without explicit bucket key."
                )

            if not force and cadence and derived_bucket_key:
                if InventorySnapshot.objects.filter(
                    trigger_source=InventorySnapshotTriggerSource.SCHEDULED,
                    cadence=cadence,
                    bucket_key=derived_bucket_key,
                ).exists():
                    raise WarehouseGenericError(
                        f"Snapshot already exists for cadence '{cadence}' and bucket '{derived_bucket_key}'."
                    )

        items = list(
            WarehouseItem.physical_stock.select_related(
                "stock_product",
                "stock_product__unit_of_measure",
                "location",
                "source_order_item",
                "source_order_item__warehouse_order",
                "source_order_item__warehouse_order__order",
            ).order_by("stock_product__code", "location__code", "pk")
        )

        purchase_totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        receipt_totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        receipt_unpriced_line_count = 0

        with transaction.atomic():
            snapshot = InventorySnapshot.objects.create(
                captured_at=captured_at,
                trigger_source=trigger_source,
                cadence=cadence,
                bucket_key=derived_bucket_key,
            )

            lines: list[InventorySnapshotLine] = []
            for item in items:
                purchase_currency = item.stock_product.currency
                purchase_unit_price = cls._quantize(item.stock_product.purchase_price)
                purchase_line_value = cls._quantize(item.amount * purchase_unit_price)
                purchase_totals[purchase_currency] += purchase_line_value

                receipt_currency: str | None = None
                receipt_unit_price: Decimal | None = None
                receipt_line_value: Decimal | None = None
                receipt_price_available = False
                receipt_price_fallback_reason: str | None = None

                if item.source_order_item:
                    receipt_currency = (
                        item.source_order_item.warehouse_order.order.currency
                    )
                    receipt_unit_price = cls._quantize(
                        item.source_order_item.unit_price_at_receipt
                    )
                    receipt_line_value = cls._quantize(item.amount * receipt_unit_price)
                    receipt_price_available = True
                    receipt_totals[receipt_currency] += receipt_line_value
                else:
                    receipt_unpriced_line_count += 1
                    receipt_price_fallback_reason = "missing_source_order_item"

                lines.append(
                    InventorySnapshotLine(
                        snapshot=snapshot,
                        warehouse_item=item,
                        warehouse_item_id_at_snapshot=item.pk,
                        stock_product=item.stock_product,
                        product_code=item.stock_product.code,
                        product_name=item.stock_product.name,
                        location=item.location,
                        location_code=item.location.code,
                        source_order_item=item.source_order_item,
                        quantity=item.amount,
                        unit_of_measure=item.stock_product.unit_of_measure.name,
                        tracking_level=item.tracking_level,
                        purchase_currency=purchase_currency,
                        purchase_unit_price=purchase_unit_price,
                        purchase_line_value=purchase_line_value,
                        receipt_currency=receipt_currency,
                        receipt_unit_price=receipt_unit_price,
                        receipt_line_value=receipt_line_value,
                        receipt_price_available=receipt_price_available,
                        receipt_price_fallback_reason=receipt_price_fallback_reason,
                    )
                )

            InventorySnapshotLine.objects.bulk_create(lines)

            snapshot.line_count = len(lines)
            snapshot.purchase_totals_by_currency = cls._serialize_totals(
                purchase_totals
            )
            snapshot.receipt_totals_by_currency = cls._serialize_totals(receipt_totals)
            snapshot.receipt_unpriced_line_count = receipt_unpriced_line_count
            snapshot.save(
                update_fields=[
                    "line_count",
                    "purchase_totals_by_currency",
                    "receipt_totals_by_currency",
                    "receipt_unpriced_line_count",
                    "changed",
                ]
            )

        return cls.get_snapshot(snapshot.pk)


inventory_snapshot_service = InventorySnapshotService()
