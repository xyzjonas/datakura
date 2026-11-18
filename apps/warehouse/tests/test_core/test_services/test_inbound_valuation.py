from decimal import Decimal

import pytest

from apps.warehouse.core.schemas.warehouse import WarehouseOrderCreateSchema
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    InboundWarehouseOrderItem,
    InboundWarehouseOrderState,
)
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    InboundWarehouseOrderItemFactory,
    WarehouseLocationFactory,
)


def arrived_order(context, *, prices=("10",), currency="CZK") -> InboundWarehouseOrder:
    """Parent order -> warehouse order with arrival confirmed (DRAFT)."""
    parent = InboundOrderFactory.it(currency=currency)
    for price in prices:
        InboundOrderItemFactory(
            order=parent,
            stock_product=StockProductFactory(),
            amount=Decimal("2"),
            unit_price=Decimal(price),
        )
    created = warehouse_service.create_inbound_order(
        WarehouseOrderCreateSchema(purchase_order_code=str(parent.code)),
        context=context,
    )
    warehouse_service.confirm_arrival(
        str(created.code),
        str(WarehouseLocationFactory(is_putaway=True).code),
        context=context,
    )
    return InboundWarehouseOrder.objects.get(code=created.code)


def test_arrival_links_each_item_to_its_parent_line(db, context):
    w_order = arrived_order(context, prices=("10", "20"))

    items = list(w_order.order_items.order_by("index"))
    parent_items = list(w_order.order.items.order_by("index"))  # type: ignore[union-attr]
    assert [i.source_order_item for i in items] == parent_items
    assert w_order.valued_at is None  # not frozen before the confirmation


@pytest.mark.parametrize("new_price", ["0", "5.5", "10", "99.9999"])
def test_confirm_draft_freezes_prices_from_parent_at_confirmation(
    db, context, new_price
):
    w_order = arrived_order(context, prices=("10", "20"), currency="EUR")
    parent_item = w_order.order.items.order_by("index").first()  # type: ignore[union-attr]
    parent_item.unit_price = Decimal(new_price)
    parent_item.save(update_fields=["unit_price"])

    warehouse_service.confirm_draft(w_order.code, context=context)

    w_order.refresh_from_db()
    prices = [i.unit_price_at_receipt for i in w_order.order_items.order_by("index")]
    assert prices == [Decimal(new_price), Decimal("20")]
    assert w_order.currency == "EUR"
    assert w_order.valued_at is not None
    assert w_order.state == InboundWarehouseOrderState.PENDING


def test_parent_changes_after_confirmation_do_not_matter(db, context):
    w_order = arrived_order(context, prices=("10",), currency="EUR")
    warehouse_service.confirm_draft(w_order.code, context=context)

    parent = w_order.order
    assert parent is not None
    parent.currency = "USD"
    parent.save(update_fields=["currency"])
    parent.items.update(unit_price=Decimal("777"))

    w_order.refresh_from_db()
    [item] = w_order.order_items.all()
    assert item.unit_price_at_receipt == Decimal("10")
    assert w_order.currency == "EUR"


def test_confirm_draft_keeps_price_of_rows_without_parent_line(db, context):
    w_order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.DRAFT)
    w_order.pickup_location = WarehouseLocationFactory(is_putaway=True)
    w_order.save()
    InboundWarehouseOrderItemFactory(
        warehouse_order=w_order,
        stock_product=StockProductFactory(),
        amount=Decimal("1"),
        unit_price_at_receipt=Decimal("42"),
        source_order_item=None,
    )

    warehouse_service.confirm_draft(w_order.code, context=context)

    [item] = InboundWarehouseOrderItem.objects.filter(warehouse_order=w_order)
    assert item.unit_price_at_receipt == Decimal("42")


def test_offloaded_item_keeps_parent_line_link(db, context):
    w_order = arrived_order(context, prices=("10",))
    [item] = w_order.order_items.all()

    warehouse_service.offload_items_to_child_order(
        w_order.code, [(item.pk, Decimal("1"))], context
    )

    child = w_order.derived_orders.get()
    [moved] = child.order_items.all()
    assert moved.source_order_item is not None
    assert moved.source_order_item == item.source_order_item
    assert child.currency == w_order.currency


@pytest.mark.parametrize(
    ("target", "expect_date"),
    [
        (InboundWarehouseOrderState.COMPLETED, True),
        (InboundWarehouseOrderState.STARTED, False),
    ],
)
def test_completed_date_follows_completion(db, context, target, expect_date):
    w_order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)

    warehouse_service.transition_order(w_order.code, target, context=context)

    w_order.refresh_from_db()
    assert (w_order.completed_date is not None) is expect_date


def test_leaving_completed_clears_completed_date(db, context):
    w_order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)
    warehouse_service.transition_order(
        w_order.code, InboundWarehouseOrderState.COMPLETED, context=context
    )
    warehouse_service.transition_order(
        w_order.code, InboundWarehouseOrderState.STARTED, context=context
    )

    w_order.refresh_from_db()
    assert w_order.completed_date is None
