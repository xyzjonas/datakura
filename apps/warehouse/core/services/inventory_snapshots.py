from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.warehouse.core.exceptions import WarehouseGenericError
from apps.warehouse.core.schemas.analytics import (
    InventorySnapshotCurrencyTotal,
    InventorySnapshotDetailSchema,
    InventorySnapshotLineSchema,
    InventorySnapshotOrderSchema,
    InventorySnapshotSummarySchema,
    LatestInventoryValueSchema,
)
from apps.warehouse.models.orders import InboundOrder, InboundOrderState
from apps.warehouse.models.warehouse import (
    InventorySnapshot,
    InventorySnapshotLine,
    InventorySnapshotOrder,
    InventorySnapshotOrderKind,
    InventorySnapshotTriggerSource,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderState,
    WarehouseItem,
)


def cast_datetime(value: datetime | None) -> datetime:
    assert value is not None  # guaranteed by the completed_date window filter
    return value


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
            period_start=snapshot.period_start,
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
            expenditure_totals=cls._deserialize_totals(
                snapshot.expenditure_totals_by_currency
            ),
            gain_totals=cls._deserialize_totals(snapshot.gain_totals_by_currency),
        )

    @staticmethod
    def line_to_schema(line: InventorySnapshotLine) -> InventorySnapshotLineSchema:
        return InventorySnapshotLineSchema(
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

    @staticmethod
    def _order_to_schema(order: InventorySnapshotOrder) -> InventorySnapshotOrderSchema:
        return InventorySnapshotOrderSchema(
            id=order.pk,
            kind=order.kind,  # type: ignore[arg-type]
            code=order.code,
            base_order_code=order.base_order_code,
            external_code=order.external_code,
            description=order.description,
            counterparty_name=order.counterparty_name,
            closed_at=order.closed_at,
            currency=order.currency,
            total_value=order.total_value,
        )

    @classmethod
    def _to_detail_schema(
        cls,
        snapshot: InventorySnapshot,
    ) -> InventorySnapshotDetailSchema:
        orders = list(snapshot.orders.all())
        summary = cls._to_summary_schema(snapshot)
        return InventorySnapshotDetailSchema(
            **summary.model_dump(),
            inbound_orders=[
                cls._order_to_schema(o)
                for o in orders
                if o.kind == InventorySnapshotOrderKind.INBOUND
            ],
            outbound_orders=[
                cls._order_to_schema(o)
                for o in orders
                if o.kind == InventorySnapshotOrderKind.OUTBOUND
            ],
        )

    @staticmethod
    def get_items_queryset(snapshot_id: int, search: str | None = None):
        """Lines of a snapshot (optionally searched by product code/name or location)."""
        snapshot = InventorySnapshot.objects.get(pk=snapshot_id)
        queryset = InventorySnapshotLine.objects.filter(snapshot=snapshot)
        term = (search or "").strip()
        if term:
            queryset = queryset.filter(
                Q(product_code__icontains=term)
                | Q(product_name__icontains=term)
                | Q(location_code__icontains=term)
            )
        return queryset

    @classmethod
    def _collect_closed_orders(
        cls,
        snapshot: InventorySnapshot,
        *,
        since: datetime | None,
        until: datetime,
    ) -> tuple[list[InventorySnapshotOrder], dict[str, Decimal], dict[str, Decimal]]:
        """
        Freeze skeletons of orders closed in (since, until].

        Inbound: purchase orders (COMPLETED), valued by their purchase total.
        Outbound: *warehouse* orders (COMPLETED) valued by the total price at
        shipment ("Celková cena výdeje") - deliberately not the base order total.
        """
        closed_window = Q(completed_date__lte=until)
        if since is not None:
            closed_window &= Q(completed_date__gt=since)

        expenditures: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        gains: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        rows: list[InventorySnapshotOrder] = []

        inbound_orders = (
            InboundOrder.objects.filter(
                closed_window, state=InboundOrderState.COMPLETED
            )
            .select_related("supplier")
            .annotate(purchase_total=Sum("items__total_price"))
            .order_by("completed_date", "pk")
        )
        for inbound in inbound_orders:
            total = cls._quantize(inbound.purchase_total or Decimal("0"))
            expenditures[inbound.currency] += total
            rows.append(
                InventorySnapshotOrder(
                    snapshot=snapshot,
                    kind=InventorySnapshotOrderKind.INBOUND,
                    inbound_order=inbound,
                    code=inbound.code,
                    base_order_code=inbound.code,
                    external_code=inbound.external_code,
                    description=inbound.description,
                    counterparty_name=inbound.supplier.name,
                    closed_at=cast_datetime(inbound.completed_date),
                    currency=inbound.currency,
                    total_value=total,
                )
            )

        outbound_orders = (
            OutboundWarehouseOrder.objects.filter(
                closed_window,
                state=OutboundWarehouseOrderState.COMPLETED,
                order__isnull=False,
            )
            .select_related("order", "order__customer")
            .annotate(shipment_total=Sum("order_items__price_at_shipment"))
            .order_by("completed_date", "pk")
        )
        for outbound in outbound_orders:
            base_order = outbound.order
            assert base_order is not None
            total = cls._quantize(outbound.shipment_total or Decimal("0"))
            gains[base_order.currency] += total
            rows.append(
                InventorySnapshotOrder(
                    snapshot=snapshot,
                    kind=InventorySnapshotOrderKind.OUTBOUND,
                    outbound_warehouse_order=outbound,
                    code=outbound.code,
                    base_order_code=base_order.code,
                    external_code=base_order.external_code,
                    description=base_order.description,
                    counterparty_name=base_order.customer.name,
                    closed_at=cast_datetime(outbound.completed_date),
                    currency=base_order.currency,
                    total_value=total,
                )
            )

        return rows, expenditures, gains

    @staticmethod
    def list_snapshots_queryset():
        return InventorySnapshot.objects.all()

    @classmethod
    def get_snapshot(cls, snapshot_id: int) -> InventorySnapshotDetailSchema:
        snapshot = InventorySnapshot.objects.prefetch_related("orders").get(
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

        previous = (
            InventorySnapshot.objects.filter(captured_at__lt=captured_at)
            .order_by("-captured_at", "-created")
            .first()
        )

        with transaction.atomic():
            snapshot = InventorySnapshot.objects.create(
                captured_at=captured_at,
                period_start=previous.captured_at if previous else None,
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

            InventorySnapshotLine.objects.bulk_create(lines, batch_size=1000)

            order_rows, expenditures, gains = cls._collect_closed_orders(
                snapshot,
                since=previous.captured_at if previous else None,
                until=captured_at,
            )
            InventorySnapshotOrder.objects.bulk_create(order_rows)

            snapshot.line_count = len(lines)
            snapshot.purchase_totals_by_currency = cls._serialize_totals(
                purchase_totals
            )
            snapshot.receipt_totals_by_currency = cls._serialize_totals(receipt_totals)
            snapshot.receipt_unpriced_line_count = receipt_unpriced_line_count
            snapshot.expenditure_totals_by_currency = cls._serialize_totals(
                expenditures
            )
            snapshot.gain_totals_by_currency = cls._serialize_totals(gains)
            snapshot.save(
                update_fields=[
                    "line_count",
                    "purchase_totals_by_currency",
                    "receipt_totals_by_currency",
                    "receipt_unpriced_line_count",
                    "expenditure_totals_by_currency",
                    "gain_totals_by_currency",
                    "changed",
                ]
            )

        return cls.get_snapshot(snapshot.pk)


inventory_snapshot_service = InventorySnapshotService()
