import pytest
from decimal import Decimal
from ninja.testing import TestClient

from apps.warehouse.api.routes.warehouse import routes
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.services.warehouse import WarehouseService
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


def test_assign_outbound_warehouse_order_item_freezes_price_at_shipment(db) -> None:
    """price_at_shipment = amount × product.purchase_price at time of picking"""
    client = TestClient(routes)

    product = StockProductFactory.it(purchase_price=Decimal("12.50"))
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
    requirement.refresh_from_db()
    # price_at_shipment must be frozen: amount(4) × purchase_price(12.50) = 50.00
    assert requirement.price_at_shipment == Decimal("50.00")

    data = res.json()["data"]
    order_item_data = next(i for i in data["order_items"] if i["id"] == requirement.pk)
    assert order_item_data["price_at_shipment"] is not None
    assert float(order_item_data["price_at_shipment"]) == pytest.approx(50.00)


def test_total_price_at_shipment_is_sum_of_assigned_items(db) -> None:
    """total_price_at_shipment on order = sum of price_at_shipment of assigned items"""
    client = TestClient(routes)

    product = StockProductFactory.it(purchase_price=Decimal("10.00"))
    outbound_order = OutboundOrderFactory.it()
    source_item_a = OutboundOrderItemFactory.it(
        order=outbound_order, stock_product=product, amount=3
    )
    source_item_b = OutboundOrderItemFactory.it(
        order=outbound_order, stock_product=product, amount=2
    )
    warehouse_order: OutboundWarehouseOrder = WarehouseOrderOutFactory.it(
        order=outbound_order, state=OutboundWarehouseOrderState.PENDING
    )
    req_a: OutboundWarehouseOrderItem = OutboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        source_order_item=source_item_a,
        stock_product=product,
        amount=3,
    )
    req_b: OutboundWarehouseOrderItem = OutboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        source_order_item=source_item_b,
        stock_product=product,
        amount=2,
    )
    source_inbound = InboundWarehouseOrderFactory(
        state=InboundWarehouseOrderState.PENDING
    )
    location = WarehouseLocationFactory(is_putaway=False)
    item_a: WarehouseItem = WarehouseItemFactory.it(
        order_in=source_inbound, stock_product=product, amount=3, location=location
    )
    item_b: WarehouseItem = WarehouseItemFactory.it(
        order_in=source_inbound, stock_product=product, amount=2, location=location
    )

    # Assign only first item
    client.post(
        f"/orders-outgoing/{warehouse_order.code}/order-items/{req_a.pk}/assign",
        json={"warehouse_item_id": item_a.pk},
    )
    res = client.post(
        f"/orders-outgoing/{warehouse_order.code}/order-items/{req_b.pk}/assign",
        json={"warehouse_item_id": item_b.pk},
    )

    assert res.status_code == 200
    data = res.json()["data"]
    # 3×10 + 2×10 = 50
    assert float(data["total_price_at_shipment"]) == pytest.approx(50.00)


def test_price_at_shipment_is_null_for_unassigned_items(db) -> None:
    """Unassigned order items have price_at_shipment=null in API response"""
    client = TestClient(routes)
    product = StockProductFactory.it()
    outbound_order = OutboundOrderFactory.it()
    source_order_item = OutboundOrderItemFactory.it(
        order=outbound_order, stock_product=product, amount=4
    )
    warehouse_order: OutboundWarehouseOrder = WarehouseOrderOutFactory.it(
        order=outbound_order, state=OutboundWarehouseOrderState.PENDING
    )
    OutboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        source_order_item=source_order_item,
        stock_product=product,
        amount=4,
    )

    res = client.get(f"/orders-outgoing/{warehouse_order.code}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["order_items"][0]["price_at_shipment"] is None
    assert float(data["total_price_at_shipment"]) == 0.0


def test_pick_clears_warehouse_item_location(db) -> None:
    """Picking a warehouse item sets its location to None (bug #5 fix)."""
    client = TestClient(routes)
    product = StockProductFactory()
    outbound_order = OutboundOrderFactory.it()
    source_order_item = OutboundOrderItemFactory.it(
        order=outbound_order, stock_product=product, amount=4
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
    matching_item.refresh_from_db()
    assert matching_item.location is None, (
        "Picked item must have location cleared to None"
    )

    # API response must expose location as null
    order_item_data = next(
        i for i in res.json()["data"]["order_items"] if i["id"] == requirement.pk
    )
    assert order_item_data["warehouse_item"]["location"] is None


def test_cancel_outbound_warehouse_order_restores_item_location(db) -> None:
    """Cancelling a warehouse order restores picked items to their original location."""
    product = StockProductFactory()
    outbound_order = OutboundOrderFactory.it()
    source_order_item = OutboundOrderItemFactory.it(
        order=outbound_order, stock_product=product, amount=4
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
    original_location = WarehouseLocationFactory(is_putaway=False)
    matching_item: WarehouseItem = WarehouseItemFactory.it(
        order_in=source_inbound,
        stock_product=product,
        amount=4,
        location=original_location,
    )

    # Pick the item (location becomes None)
    ctx = RequestContext(user_id=None)
    WarehouseService.assign_outbound_item(
        warehouse_order_code=warehouse_order.code,
        order_item_id=requirement.pk,
        warehouse_item_id=matching_item.pk,
        context=ctx,
    )
    matching_item.refresh_from_db()
    assert matching_item.location is None

    # Cancel the order — location must be restored
    WarehouseService.cancel_outbound_warehouse_order(warehouse_order, ctx)
    matching_item.refresh_from_db()
    assert matching_item.location == original_location, (
        "Cancelled pick must restore item location to original"
    )
