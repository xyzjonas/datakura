import pytest

from apps.warehouse.core.services.orders import inbound_orders_service
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.orders import InboundOrderState
from apps.warehouse.models.warehouse import OutboundWarehouseOrderState
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    OutboundWarehouseOrderItemFactory,
    WarehouseItemFactory,
    WarehouseOrderOutFactory,
)


def test_inbound_order_completion_stamps_and_rollback_clears_completed_date(
    db, context
):
    order = InboundOrderFactory(state=InboundOrderState.PUTAWAY)
    assert order.completed_date is None

    inbound_orders_service.transition_order(
        order.code, context=context, target_state=InboundOrderState.COMPLETED
    )
    order.refresh_from_db()
    assert order.completed_date is not None

    inbound_orders_service.transition_order(
        order.code, context=context, target_state=InboundOrderState.PUTAWAY
    )
    order.refresh_from_db()
    assert order.completed_date is None


@pytest.mark.parametrize("assign_all", [True, False])
def test_outbound_warehouse_order_completed_date_follows_completion(
    db, context, assign_all
):
    w_order = WarehouseOrderOutFactory(state=OutboundWarehouseOrderState.STARTED)
    product = StockProductFactory()
    for _ in range(2):
        source = OutboundOrderItemFactory(order=w_order.order, stock_product=product)
        OutboundWarehouseOrderItemFactory(
            warehouse_order=w_order,
            source_order_item=source,
            warehouse_item=WarehouseItemFactory(stock_product=product, order_in=None)
            if assign_all
            else None,
        )

    warehouse_service._sync_outbound_warehouse_order_state(w_order, context)
    w_order.refresh_from_db()

    if assign_all:
        assert w_order.state == OutboundWarehouseOrderState.COMPLETED
        assert w_order.completed_date is not None
    else:
        assert w_order.state == OutboundWarehouseOrderState.PENDING
        assert w_order.completed_date is None


def test_outbound_warehouse_order_leaving_completed_clears_completed_date(db, context):
    w_order = WarehouseOrderOutFactory(state=OutboundWarehouseOrderState.COMPLETED)
    OutboundWarehouseOrderItemFactory(
        warehouse_order=w_order,
        source_order_item=OutboundOrderItemFactory(order=w_order.order),
        warehouse_item=None,
    )
    w_order.completed_date = w_order.changed
    w_order.save()

    warehouse_service._sync_outbound_warehouse_order_state(w_order, context)
    w_order.refresh_from_db()

    assert w_order.state == OutboundWarehouseOrderState.PENDING
    assert w_order.completed_date is None
