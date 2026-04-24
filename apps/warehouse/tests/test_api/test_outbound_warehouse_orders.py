from ninja.testing import TestClient

from apps.warehouse.api.routes.warehouse import routes
from apps.warehouse.models.orders import OutboundOrderState
from apps.warehouse.models.warehouse import (
    Batch,
    InboundWarehouseOrderState,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderItem,
    OutboundWarehouseOrderState,
    WarehouseItem,
    WarehouseMovement,
)
from apps.warehouse.tests.factories.order import (
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.packaging import PackageTypeFactory
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    OutboundWarehouseOrderItemFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
    WarehouseOrderOutFactory,
)


def test_get_outbound_warehouse_item_candidates_filters_by_package_and_batch(
    db,
) -> None:
    client = TestClient(routes)
    product = StockProductFactory()
    package = PackageTypeFactory(unit_of_measure=product.unit_of_measure, amount=2)
    good_batch = Batch.objects.create()
    good_batch.attach_barcode("CAND-BATCH-001", is_primary=True)
    other_batch = Batch.objects.create()
    other_batch.attach_barcode("CAND-BATCH-002", is_primary=True)

    outbound_order = OutboundOrderFactory.it()
    source_order_item = OutboundOrderItemFactory.it(
        order=outbound_order,
        stock_product=product,
        amount=4,
        desired_package_type=package,
        desired_batch=good_batch,
    )
    warehouse_order: OutboundWarehouseOrder = WarehouseOrderOutFactory.it(
        order=outbound_order, state=OutboundWarehouseOrderState.PENDING
    )
    requirement: OutboundWarehouseOrderItem = OutboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        source_order_item=source_order_item,
        stock_product=product,
        amount=4,
        desired_package_type=package,
        desired_batch=good_batch,
    )

    source_inbound = InboundWarehouseOrderFactory(
        state=InboundWarehouseOrderState.PENDING
    )
    location = WarehouseLocationFactory(is_putaway=False)
    matching_item: WarehouseItem = WarehouseItemFactory.it(
        order_in=source_inbound,
        stock_product=product,
        amount=4,
        package_type=package,
        batch=good_batch,
        location=location,
    )
    WarehouseItemFactory(
        order_in=source_inbound,
        stock_product=product,
        amount=4,
        package_type=package,
        batch=other_batch,
        location=location,
    )

    res = client.get(
        f"/orders-outgoing/{warehouse_order.code}/order-items/{requirement.pk}/candidates"
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert [item["id"] for item in data] == [matching_item.pk]


def test_assign_outbound_warehouse_order_item_marks_order_completed(db) -> None:
    client = TestClient(routes)
    product = StockProductFactory()
    outbound_order = OutboundOrderFactory.it()
    source_order_item = OutboundOrderItemFactory.it(
        order=outbound_order,
        stock_product=product,
        amount=4,
    )
    warehouse_order: OutboundWarehouseOrder = WarehouseOrderOutFactory.it(
        order=outbound_order, state=OutboundWarehouseOrderState.PENDING
    )
    requirement: OutboundWarehouseOrderItem = OutboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        source_order_item=source_order_item,
        stock_product=product,
        amount=4,
    )
    source_inbound = InboundWarehouseOrderFactory(
        state=InboundWarehouseOrderState.PENDING
    )
    location = WarehouseLocationFactory(is_putaway=False)
    matching_item: WarehouseItem = WarehouseItemFactory.it(
        order_in=source_inbound,
        stock_product=product,
        amount=4,
        location=location,
    )

    res = client.post(
        f"/orders-outgoing/{warehouse_order.code}/order-items/{requirement.pk}/assign",
        json={"warehouse_item_id": matching_item.pk},
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["state"] == "completed"
    assert data["order_items"][0]["warehouse_item_id"] == matching_item.pk
    assert (
        WarehouseMovement.objects.filter(outbound_order_code=warehouse_order).count()
        == 1
    )
    outbound_order.refresh_from_db()
    assert outbound_order.state == OutboundOrderState.SENT


def test_get_outbound_warehouse_item_candidates_include_pending_inbound_putaway_stock(
    db,
) -> None:
    client = TestClient(routes)
    product = StockProductFactory()
    outbound_order = OutboundOrderFactory.it()
    source_order_item = OutboundOrderItemFactory.it(
        order=outbound_order,
        stock_product=product,
        amount=4,
    )
    warehouse_order: OutboundWarehouseOrder = WarehouseOrderOutFactory.it(
        order=outbound_order,
        state=OutboundWarehouseOrderState.PENDING,
    )
    requirement: OutboundWarehouseOrderItem = OutboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        source_order_item=source_order_item,
        stock_product=product,
        amount=4,
    )
    source_inbound = InboundWarehouseOrderFactory(
        state=InboundWarehouseOrderState.PENDING
    )
    putaway_location = WarehouseLocationFactory(is_putaway=True)
    matching_item: WarehouseItem = WarehouseItemFactory.it(
        order_in=source_inbound,
        stock_product=product,
        amount=4,
        location=putaway_location,
    )

    res = client.get(
        f"/orders-outgoing/{warehouse_order.code}/order-items/{requirement.pk}/candidates"
    )

    assert res.status_code == 200
    assert [item["id"] for item in res.json()["data"]] == [matching_item.pk]


def test_offload_outbound_items_to_child_order_moves_requirement(db) -> None:
    client = TestClient(routes)
    product = StockProductFactory()
    outbound_order = OutboundOrderFactory.it()
    source_order_item = OutboundOrderItemFactory.it(
        order=outbound_order,
        stock_product=product,
        amount=4,
    )
    warehouse_order: OutboundWarehouseOrder = WarehouseOrderOutFactory.it(
        order=outbound_order, state=OutboundWarehouseOrderState.PENDING
    )
    requirement: OutboundWarehouseOrderItem = OutboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        source_order_item=source_order_item,
        stock_product=product,
        amount=4,
    )

    res = client.post(
        f"/orders-outgoing/{warehouse_order.code}/offload",
        json={"items": [{"item_id": requirement.pk, "amount": 4}]},
    )

    assert res.status_code == 200
    requirement.refresh_from_db()
    assert requirement.warehouse_order.primary_order_id == warehouse_order.pk
    assert requirement.warehouse_order_id != warehouse_order.pk
