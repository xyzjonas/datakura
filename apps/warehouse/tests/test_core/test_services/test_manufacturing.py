"""
Tests for the manufacturing cost-balance invariant:

Whatever is taken out of the warehouse (frozen in the outbound order's
price_at_shipment) must come back in at the same total value, split evenly
across the output product's quantity so the warehouse avg price stays balanced.

Example: 1 m bar leaves at 10 USD → 2 × 50 cm bars come back at 5 USD each.
"""

from decimal import Decimal

import pytest

from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrderItem,
    InboundWarehouseOrderState,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderItem,
    OutboundWarehouseOrderState,
    WarehouseItem,
)
from apps.warehouse.tests.factories.manufacturing import (
    ManufacturingOrderFactory,
    ManufacturingOrderItemFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
)


def _make_outbound_order_with_frozen_cost(
    mfg_order,
    mfg_item,
    frozen_total_cost: Decimal,
) -> OutboundWarehouseOrder:
    """Create an COMPLETED outbound warehouse order whose price_at_shipment is frozen."""
    outbound_order = OutboundWarehouseOrder.objects.create(
        code=f"VTEST-{mfg_order.pk}",
        manufacturing_order=mfg_order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )
    OutboundWarehouseOrderItem.objects.create(
        warehouse_order=outbound_order,
        source_manufacturing_item=mfg_item,
        stock_product=mfg_item.in_product,
        amount=mfg_item.in_amount,
        price_at_shipment=frozen_total_cost,
        index=0,
    )
    return outbound_order


def _make_inbound_order_in_transit(mfg_order, pickup_location):
    """Create a manufacturing-linked inbound warehouse order in IN_TRANSIT state."""
    return InboundWarehouseOrderFactory(
        order=None,
        manufacturing_order=mfg_order,
        state=InboundWarehouseOrderState.IN_TRANSIT,
        pickup_location=pickup_location,
    )


@pytest.mark.parametrize(
    "in_amount, frozen_total_cost, out_amount, expected_unit_price",
    [
        # Basic: 1m bar → 2×50cm, cost=10 → 5 each
        (Decimal("1"), Decimal("10"), Decimal("2"), Decimal("5")),
        # Same cost, 1 output → unit price equals total cost
        (Decimal("1"), Decimal("10"), Decimal("1"), Decimal("10")),
        # 3 pieces from 1 bar: 10/3 each — stored at 4dp precision as 3.3333
        (Decimal("1"), Decimal("10"), Decimal("3"), Decimal("3.3333")),
        # Odd cost: 7/2 = 3.5
        (Decimal("2"), Decimal("7"), Decimal("2"), Decimal("3.5")),
        # Large batch: 100 units out from 30 cost → 0.3 each
        (Decimal("5"), Decimal("30"), Decimal("100"), Decimal("0.3")),
        # Cost is zero (e.g. already fully consumed product, edge case)
        (Decimal("1"), Decimal("0"), Decimal("2"), Decimal("0")),
    ],
)
def test_confirm_arrival_sets_frozen_unit_price(
    db,
    context,
    in_amount,
    frozen_total_cost,
    out_amount,
    expected_unit_price,
):
    """
    confirm_arrival must populate unit_price_at_receipt on each inbound item
    using the frozen outbound cost divided by out_amount.
    """
    in_product = StockProductFactory.it(purchase_price=Decimal("10"))
    out_product = StockProductFactory.it(purchase_price=Decimal("1"))
    pickup_location = WarehouseLocationFactory(is_putaway=True)

    mfg_order = ManufacturingOrderFactory()
    mfg_item = ManufacturingOrderItemFactory(
        order=mfg_order,
        in_product=in_product,
        in_amount=in_amount,
        out_product=out_product,
        out_amount=out_amount,
    )

    _make_outbound_order_with_frozen_cost(mfg_order, mfg_item, frozen_total_cost)
    inbound_order = _make_inbound_order_in_transit(mfg_order, pickup_location)

    warehouse_service.confirm_arrival(
        inbound_order.code, pickup_location.code, context=context
    )

    order_items = list(
        InboundWarehouseOrderItem.objects.filter(warehouse_order=inbound_order)
    )
    assert len(order_items) == 1
    assert order_items[0].amount == out_amount
    assert order_items[0].unit_price_at_receipt == pytest.approx(
        expected_unit_price, abs=Decimal("0.0001")
    )


@pytest.mark.parametrize(
    "in_amount, frozen_total_cost, out_amount, existing_out_qty, existing_out_price, expected_avg",
    [
        # No existing stock: avg = incoming unit price = 10/2 = 5
        (
            Decimal("1"),
            Decimal("10"),
            Decimal("2"),
            Decimal("0"),
            Decimal("0"),
            Decimal("5"),
        ),
        # Existing 10 @ 3, incoming 2 @ 5: (30+10)/12 = 3.33 (stored at 2dp)
        (
            Decimal("1"),
            Decimal("10"),
            Decimal("2"),
            Decimal("10"),
            Decimal("3"),
            Decimal("3.33"),
        ),
        # Existing 5 @ 20, incoming 5 @ 6: (100+30)/10 = 13 (exact)
        (
            Decimal("1"),
            Decimal("30"),
            Decimal("5"),
            Decimal("5"),
            Decimal("20"),
            Decimal("13"),
        ),
        # No existing stock: avg = 7/2 = 3.5 (exact)
        (
            Decimal("1"),
            Decimal("7"),
            Decimal("2"),
            Decimal("0"),
            Decimal("0"),
            Decimal("3.5"),
        ),
        # Existing 10 @ 1, incoming 5 @ 3: (10+15)/15 = 1.67 (stored at 2dp)
        (
            Decimal("1"),
            Decimal("15"),
            Decimal("5"),
            Decimal("10"),
            Decimal("1"),
            Decimal("1.67"),
        ),
    ],
)
def test_confirm_draft_recalculates_avg_price_from_frozen_outbound_cost(
    db,
    context,
    in_amount,
    frozen_total_cost,
    out_amount,
    existing_out_qty,
    existing_out_price,
    expected_avg,
):
    """
    Full cost-balance flow: after confirm_arrival + confirm_draft the out_product's
    purchase_price (avg) must reflect the value transferred from the outbound order.
    """
    in_product = StockProductFactory.it(purchase_price=Decimal("10"))
    out_product = StockProductFactory.it(
        purchase_price=existing_out_price if existing_out_qty > 0 else Decimal("0")
    )
    pickup_location = WarehouseLocationFactory(is_putaway=True)

    if existing_out_qty > 0:
        WarehouseItemFactory(
            stock_product=out_product,
            amount=existing_out_qty,
            order_in=InboundWarehouseOrderFactory(
                state=InboundWarehouseOrderState.COMPLETED
            ),
            location=WarehouseLocationFactory(is_putaway=False),
        )

    mfg_order = ManufacturingOrderFactory()
    mfg_item = ManufacturingOrderItemFactory(
        order=mfg_order,
        in_product=in_product,
        in_amount=in_amount,
        out_product=out_product,
        out_amount=out_amount,
    )

    _make_outbound_order_with_frozen_cost(mfg_order, mfg_item, frozen_total_cost)
    inbound_order = _make_inbound_order_in_transit(mfg_order, pickup_location)

    warehouse_service.confirm_arrival(
        inbound_order.code, pickup_location.code, context=context
    )
    warehouse_service.confirm_draft(inbound_order.code, context=context)

    out_product.refresh_from_db()
    assert out_product.purchase_price == pytest.approx(
        expected_avg, abs=Decimal("0.01")
    )

    # Warehouse items for the out_product must exist and total to out_amount
    wh_items = WarehouseItem.objects.filter(
        stock_product=out_product,
        order_in=inbound_order,
    )
    assert wh_items.exists()
    total = sum(i.amount for i in wh_items)
    assert total == pytest.approx(out_amount)


def test_cost_balance_multi_item_manufacturing_order(db, context):
    """
    A manufacturing order with two items (two products being processed) must
    balance costs independently per item.

    Item 1: 1 bar (frozen cost=10) → 2 half-bars at 5 each
    Item 2: 3 sheets (frozen cost=9) → 1 panel at 9
    """
    bar = StockProductFactory.it(purchase_price=Decimal("10"))
    half_bar = StockProductFactory.it(purchase_price=Decimal("0"))
    sheet = StockProductFactory.it(purchase_price=Decimal("3"))
    panel = StockProductFactory.it(purchase_price=Decimal("0"))

    pickup_location = WarehouseLocationFactory(is_putaway=True)
    mfg_order = ManufacturingOrderFactory()

    item1 = ManufacturingOrderItemFactory(
        order=mfg_order,
        in_product=bar,
        in_amount=Decimal("1"),
        out_product=half_bar,
        out_amount=Decimal("2"),
        index=0,
    )
    item2 = ManufacturingOrderItemFactory(
        order=mfg_order,
        in_product=sheet,
        in_amount=Decimal("3"),
        out_product=panel,
        out_amount=Decimal("1"),
        index=1,
    )

    outbound_order = OutboundWarehouseOrder.objects.create(
        code="VTEST-MULTI",
        manufacturing_order=mfg_order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )
    OutboundWarehouseOrderItem.objects.create(
        warehouse_order=outbound_order,
        source_manufacturing_item=item1,
        stock_product=bar,
        amount=Decimal("1"),
        price_at_shipment=Decimal("10"),
        index=0,
    )
    OutboundWarehouseOrderItem.objects.create(
        warehouse_order=outbound_order,
        source_manufacturing_item=item2,
        stock_product=sheet,
        amount=Decimal("3"),
        price_at_shipment=Decimal("9"),
        index=1,
    )

    inbound_order = _make_inbound_order_in_transit(mfg_order, pickup_location)

    warehouse_service.confirm_arrival(
        inbound_order.code, pickup_location.code, context=context
    )
    warehouse_service.confirm_draft(inbound_order.code, context=context)

    half_bar.refresh_from_db()
    panel.refresh_from_db()

    # 10 total cost / 2 half-bars = 5 each
    assert half_bar.purchase_price == pytest.approx(Decimal("5"))
    # 9 total cost / 1 panel = 9 each
    assert panel.purchase_price == pytest.approx(Decimal("9"))
