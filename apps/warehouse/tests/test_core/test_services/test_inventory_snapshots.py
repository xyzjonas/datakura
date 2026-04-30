from decimal import Decimal
from typing import cast

import pytest

from apps.warehouse.core.exceptions import WarehouseGenericError
from apps.warehouse.core.services.inventory_snapshots import inventory_snapshot_service
from apps.warehouse.models.orders import InboundOrder
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrderState,
    InventorySnapshotTriggerSource,
)
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    InboundWarehouseOrderItemFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory


def create_snapshot_item(
    *,
    product_code: str,
    location_code: str,
    quantity: str,
    purchase_price: str,
    purchase_currency: str = "CZK",
    receipt_price: str | None = None,
    receipt_currency: str = "CZK",
):
    product = StockProductFactory(
        code=product_code,
        purchase_price=Decimal(purchase_price),
        currency=purchase_currency,
    )
    location = WarehouseLocationFactory(code=location_code)
    inbound_order = InboundWarehouseOrderFactory(
        state=InboundWarehouseOrderState.PENDING,
    )
    inbound_order_order = cast(InboundOrder, inbound_order.order)
    inbound_order_order.currency = receipt_currency
    inbound_order_order.save(update_fields=["currency"])

    source_order_item = None
    if receipt_price is not None:
        source_order_item = InboundWarehouseOrderItemFactory(
            warehouse_order=inbound_order,
            stock_product=product,
            amount=Decimal(quantity),
            unit_price_at_receipt=Decimal(receipt_price),
        )

    return WarehouseItemFactory(
        stock_product=product,
        amount=Decimal(quantity),
        location=location,
        order_in=inbound_order,
        source_order_item=source_order_item,
    )


def test_create_snapshot_freezes_purchase_and_receipt_values(db):
    item = create_snapshot_item(
        product_code="SNAP-001",
        location_code="A-01",
        quantity="5",
        purchase_price="10.00",
        receipt_price="8.50",
    )

    snapshot = inventory_snapshot_service.create_snapshot()

    item.stock_product.purchase_price = Decimal("15.00")
    item.stock_product.save(update_fields=["purchase_price"])
    assert item.source_order_item is not None
    item.source_order_item.unit_price_at_receipt = Decimal("7.00")
    item.source_order_item.save(update_fields=["unit_price_at_receipt"])

    persisted = inventory_snapshot_service.get_snapshot(snapshot.id)
    line = persisted.lines[0]

    assert line.purchase_unit_price == Decimal("10.0000")
    assert line.purchase_line_value == Decimal("50.0000")
    assert line.receipt_unit_price == Decimal("8.5000")
    assert line.receipt_line_value == Decimal("42.5000")


def test_create_snapshot_groups_purchase_and_receipt_totals_by_currency(db):
    create_snapshot_item(
        product_code="SNAP-CZK",
        location_code="B-01",
        quantity="2",
        purchase_price="11.00",
        purchase_currency="CZK",
        receipt_price="10.50",
        receipt_currency="CZK",
    )
    create_snapshot_item(
        product_code="SNAP-EUR",
        location_code="B-02",
        quantity="3",
        purchase_price="4.00",
        purchase_currency="EUR",
        receipt_price="3.50",
        receipt_currency="EUR",
    )

    snapshot = inventory_snapshot_service.create_snapshot()

    purchase_totals = {row.currency: row.value for row in snapshot.purchase_totals}
    receipt_totals = {row.currency: row.value for row in snapshot.receipt_totals}

    assert purchase_totals == {
        "CZK": Decimal("22.0000"),
        "EUR": Decimal("12.0000"),
    }
    assert receipt_totals == {
        "CZK": Decimal("21.0000"),
        "EUR": Decimal("10.5000"),
    }


def test_create_scheduled_snapshot_rejects_duplicate_bucket(db):
    create_snapshot_item(
        product_code="SNAP-DUP",
        location_code="C-01",
        quantity="1",
        purchase_price="1.00",
        receipt_price="1.00",
    )

    inventory_snapshot_service.create_snapshot(
        trigger_source=InventorySnapshotTriggerSource.SCHEDULED,
        cadence="daily",
        bucket_key="2026-04-28",
    )

    with pytest.raises(WarehouseGenericError):
        inventory_snapshot_service.create_snapshot(
            trigger_source=InventorySnapshotTriggerSource.SCHEDULED,
            cadence="daily",
            bucket_key="2026-04-28",
        )
