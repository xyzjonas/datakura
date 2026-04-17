from datetime import timedelta
from typing import cast

import pytest
from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.warehouse import routes
from apps.warehouse.core.exceptions import (
    WarehouseGenericError,
    WarehouseItemNotFoundError,
)
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrderState,
    OutboundWarehouseOrderState,
    TrackingLevel,
    WarehouseItem,
    WarehouseMovement,
)
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderItemFactory,
    InboundWarehouseOrderFactory,
    OutboundWarehouseOrderItemFactory,
    WarehouseOrderOutFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def test_putaway_item(db, client) -> None:
    order = InboundWarehouseOrderFactory.create_complete(
        state=InboundWarehouseOrderState.PENDING
    )
    item = order.items.first()
    assert item
    new_location = WarehouseLocationFactory()

    res = client.post(
        f"orders-incoming/{order.code}/items/{item.pk}/putaway",
        json={"new_location_code": new_location.code},
    )

    assert res.status_code == 200
    item.refresh_from_db()
    assert item.location == new_location


def test_get_outbound_warehouse_orders(db, client) -> None:
    order = WarehouseOrderOutFactory.it(state=OutboundWarehouseOrderState.PENDING)

    res = client.get("orders-outgoing")

    assert res.status_code == 200
    rows = res.json()["data"]
    assert len([row for row in rows if row["code"] == order.code]) == 1


def test_get_outbound_warehouse_order(db, client) -> None:
    order = WarehouseOrderOutFactory.it(state=OutboundWarehouseOrderState.PENDING)
    linked_order = order.order
    assert linked_order is not None

    res = client.get(f"orders-outgoing/{order.code}")

    assert res.status_code == 200
    payload = res.json()["data"]
    assert payload["code"] == order.code
    assert payload["order"]["code"] == linked_order.code


def test_get_inbound_order_item_shows_outbound_link_and_done_when_assigned(
    db, client
) -> None:
    inbound_order = InboundWarehouseOrderFactory.create_complete(
        state=InboundWarehouseOrderState.PENDING
    )
    inbound_item = inbound_order.order_items.first()
    warehouse_item = inbound_order.items.first()
    assert inbound_item is not None
    assert warehouse_item is not None

    outbound_order = OutboundOrderFactory.it()
    source_order_item = OutboundOrderItemFactory(
        order=outbound_order,
        stock_product=warehouse_item.stock_product,
        amount=warehouse_item.amount,
    )
    outbound_warehouse_order = WarehouseOrderOutFactory(
        order=outbound_order,
        state=OutboundWarehouseOrderState.STARTED,
    )
    OutboundWarehouseOrderItemFactory(
        warehouse_order=outbound_warehouse_order,
        source_order_item=source_order_item,
        stock_product=warehouse_item.stock_product,
        amount=warehouse_item.amount,
        warehouse_item=warehouse_item,
    )

    res = client.get(f"orders-incoming/{inbound_order.code}")

    assert res.status_code == 200
    payload = res.json()["data"]
    row = next(i for i in payload["order_items"] if i["id"] == inbound_item.pk)
    assert row["outbound_order_code"] == outbound_warehouse_order.code
    assert row["pending"] is False


def test_putaway_item_invalid_state(db, client) -> None:
    order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.DRAFT)
    item: WarehouseItem = WarehouseItemFactory(order_in=order)  # type: ignore
    new_location = WarehouseLocationFactory()

    with pytest.raises(WarehouseGenericError):
        client.post(
            f"orders-incoming/{order.code}/items/{item.pk}/putaway",
            json={"new_location_code": new_location.code},
        )


def test_putaway_item_merge(db, client) -> None:
    order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)
    item_to_move: WarehouseItem = WarehouseItemFactory(order_in=order)  # type: ignore
    InboundOrderItemFactory(order=order.order, stock_product=item_to_move.stock_product)
    original_amount = item_to_move.amount

    new_location = WarehouseLocationFactory()
    existing_item: WarehouseItem = WarehouseItemFactory(  # type: ignore
        location=new_location,
        stock_product=item_to_move.stock_product,
    )
    existing_amount = existing_item.amount

    res = client.post(
        f"orders-incoming/{order.code}/items/{item_to_move.pk}/putaway",
        json={"new_location_code": new_location.code},
    )

    assert res.status_code == 200

    with pytest.raises(WarehouseItem.DoesNotExist):
        WarehouseItem.objects.get(pk=item_to_move.pk)

    existing_item.refresh_from_db()
    assert existing_item.amount == existing_amount + original_amount


def test_get_locations_filter_by_stock_product(db, client) -> None:
    location_with_item = WarehouseLocationFactory()
    WarehouseLocationFactory()  # without item
    item = WarehouseItemFactory(location=location_with_item)
    stock_product = cast(StockProduct, item.stock_product)

    res = client.get(f"/locations?stock_product_code={stock_product.code}")

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["code"] == location_with_item.code


def test_get_warehouse_item_detail(db, client) -> None:
    item = WarehouseItemFactory.it()
    destination = WarehouseLocationFactory.it()

    created_log = audit_service.add_entry(
        obj=item,
        action=AuditAction.UPDATE,
        reason=AuditMessages.CORRECTED_QUANTITY.CS,
    )
    movement = WarehouseMovement.objects.create(
        location_from=item.location,
        location_to=destination,
        stock_product=item.stock_product,
        amount=item.amount,
        item=item,
    )
    now = timezone.now()
    WarehouseMovement.objects.filter(pk=movement.pk).update(moved_at=now)
    AuditLog.objects.filter(pk=created_log.pk).update(created=now - timedelta(hours=1))  # type: ignore

    res = client.get(f"items/{item.pk}")

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["id"] == item.pk
    assert data["product"]["code"] == item.stock_product.code
    assert data["location"]["code"] == item.location.code
    assert len(data["audits"]) == 2
    assert data["audits"][0]["source"] == "movement"
    assert data["audits"][0]["action"] == AuditAction.TRANSITION
    assert data["audits"][1]["source"] == "audit"
    assert data["audits"][1]["action"] == AuditAction.UPDATE


def test_get_warehouse_item_detail_not_found(db, client) -> None:
    with pytest.raises(WarehouseItemNotFoundError):
        client.get("items/999999")


def test_get_inbound_warehouse_order_includes_movements_desc(db, client) -> None:
    order = InboundWarehouseOrderFactory.create_complete(
        state=InboundWarehouseOrderState.PENDING
    )
    item = order.items.first()
    assert item
    location_a = WarehouseLocationFactory.it()
    location_b = WarehouseLocationFactory.it()

    older = WarehouseMovement.objects.create(
        location_from=location_a,
        location_to=location_b,
        inbound_order_code=order,
        stock_product=item.stock_product,
        amount=1,
        item=item,
    )
    newer = WarehouseMovement.objects.create(
        location_from=location_b,
        location_to=location_a,
        inbound_order_code=order,
        stock_product=item.stock_product,
        amount=2,
        item=item,
    )
    now = timezone.now()
    WarehouseMovement.objects.filter(pk=older.pk).update(
        moved_at=now - timedelta(hours=1)
    )
    WarehouseMovement.objects.filter(pk=newer.pk).update(moved_at=now)

    res = client.get(f"orders-incoming/{order.code}")

    assert res.status_code == 200
    data = res.json()["data"]
    movements = data["movements"]
    assert len(movements) == 2
    assert movements[0]["amount"] == 2.0
    assert movements[1]["amount"] == 1.0
    assert movements[0]["stock_product"]["code"] == item.stock_product.code
    assert movements[0]["item"]["id"] == item.pk
    assert movements[0]["location_from_code"] == location_b.code
    assert movements[0]["location_to_code"] == location_a.code


def test_get_inbound_warehouse_order_audits(db, client) -> None:
    order = InboundWarehouseOrderFactory.create_complete(
        state=InboundWarehouseOrderState.PENDING
    )
    item = order.items.first()
    assert item
    location_a = WarehouseLocationFactory.it()
    location_b = WarehouseLocationFactory.it()

    audit_log = audit_service.add_entry(
        order,
        action=AuditAction.UPDATE,
        reason=AuditMessages.WAREHOUSE_ORDER_ADJUSTED.CS,
    )
    movement = WarehouseMovement.objects.create(
        location_from=location_a,
        location_to=location_b,
        inbound_order_code=order,
        stock_product=item.stock_product,
        amount=1,
        item=item,
    )

    now = timezone.now()
    AuditLog.objects.filter(pk=audit_log.pk).update(created=now - timedelta(hours=1))  # type: ignore
    WarehouseMovement.objects.filter(pk=movement.pk).update(moved_at=now)

    res = client.get(f"orders-incoming/{order.code}/audits")

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 2
    assert data[0]["source"] == "movement"
    assert data[0]["action"] == AuditAction.TRANSITION
    assert data[1]["source"] == "audit"
    assert data[1]["action"] == AuditAction.UPDATE


def test_get_inbound_warehouse_order_includes_total_and_remaining_amount(
    db, client, context
) -> None:
    putaway_location = WarehouseLocationFactory(is_putaway=True)
    order = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.PENDING)
    to_be_moved_1 = WarehouseItemFactory.it(
        order_in=order, location=putaway_location, amount=10
    )
    to_be_moved_2 = WarehouseItemFactory.it(
        order_in=order, location=putaway_location, amount=10
    )

    InboundOrderItemFactory(
        order=order.order, stock_product=to_be_moved_1.stock_product, amount=10
    )
    InboundOrderItemFactory(
        order=order.order, stock_product=to_be_moved_2.stock_product, amount=10
    )
    new_location = WarehouseLocationFactory.it(is_putaway=False)

    res = client.get(f"orders-incoming/{order.code}")

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total_amount"] == 20.0
    assert data["remaining_amount"] == 20.0

    warehouse_service.putaway_item(
        item_id=to_be_moved_1.pk,
        warehouse_order_code=order.code,
        new_location_code=new_location.code,
        context=context,
    )

    res = client.get(f"orders-incoming/{order.code}")

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total_amount"] == 20.0
    assert data["remaining_amount"] == 10.0


def test_get_inbound_warehouse_orders_list_includes_movements(db, client) -> None:
    order = InboundWarehouseOrderFactory.create_complete(
        state=InboundWarehouseOrderState.PENDING
    )
    item = order.items.first()
    assert item
    src = WarehouseLocationFactory.it()
    dst = WarehouseLocationFactory.it()

    WarehouseMovement.objects.create(
        location_from=src,
        location_to=dst,
        inbound_order_code=order,
        stock_product=item.stock_product,
        amount=3,
        item=item,
    )

    res = client.get("orders-incoming")

    assert res.status_code == 200
    rows = res.json()["data"]
    matching = [row for row in rows if row["code"] == order.code]
    assert len(matching) == 1
    assert len(matching[0]["movements"]) == 1
    movement = matching[0]["movements"][0]
    assert movement["amount"] == 3


def test_transition_inbound_order_from_in_transit_to_draft_creates_items(db, client):
    receiving_location = WarehouseLocationFactory(is_putaway=True)
    inbound_order = InboundOrderFactory()
    InboundOrderItemFactory.create_batch(2, order=inbound_order)
    warehouse_order = InboundWarehouseOrderFactory(
        order=inbound_order,
        state=InboundWarehouseOrderState.IN_TRANSIT,
    )

    res = client.post(
        f"orders-incoming/{warehouse_order.code}/transition",
        json={"location_code": receiving_location.code},
    )

    assert res.status_code == 200
    warehouse_order.refresh_from_db()
    assert warehouse_order.state == InboundWarehouseOrderState.DRAFT
    assert warehouse_order.order_items.count() == 2
    assert warehouse_order.pickup_location.code == receiving_location.code


def test_get_inbound_warehouse_order_marks_draft_order_items_pending(
    db, client
) -> None:
    order = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)
    order_item = InboundWarehouseOrderItemFactory.it(warehouse_order=order)

    res = client.get(f"orders-incoming/{order.code}")

    assert res.status_code == 200
    payload = res.json()["data"]
    returned_item = next(
        item for item in payload["order_items"] if item["id"] == order_item.pk
    )
    assert returned_item["pending"] is True


def test_get_inbound_warehouse_order_marks_tracked_stored_order_item_done(
    db, client
) -> None:
    order = InboundWarehouseOrderFactory.create_complete(
        state=InboundWarehouseOrderState.PENDING,
        is_putaway=False,
    )
    order_item = order.order_items.first()
    warehouse_item = order.items.first()
    assert order_item is not None
    assert warehouse_item is not None

    order_item.tracking_level = TrackingLevel.BATCH
    order_item.save(update_fields=["tracking_level"])
    warehouse_item.tracking_level = TrackingLevel.BATCH
    warehouse_item.save(update_fields=["tracking_level"])

    res = client.get(f"orders-incoming/{order.code}")

    assert res.status_code == 200
    payload = res.json()["data"]
    returned_item = next(
        item for item in payload["order_items"] if item["id"] == order_item.pk
    )
    assert returned_item["pending"] is False


def test_get_inbound_warehouse_order_marks_fungible_order_item_without_live_link_done(
    db, client
) -> None:
    order = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.PENDING)
    order_item = InboundWarehouseOrderItemFactory.it(
        warehouse_order=order,
        tracking_level=TrackingLevel.FUNGIBLE,
    )

    res = client.get(f"orders-incoming/{order.code}")

    assert res.status_code == 200
    payload = res.json()["data"]
    returned_item = next(
        item for item in payload["order_items"] if item["id"] == order_item.pk
    )
    assert returned_item["pending"] is False


def test_transition_inbound_order_from_in_transit_to_draft_requires_location(
    db, client
):
    inbound_order = InboundOrderFactory()
    InboundOrderItemFactory.create_batch(1, order=inbound_order)
    warehouse_order = InboundWarehouseOrderFactory(
        order=inbound_order,
        state=InboundWarehouseOrderState.IN_TRANSIT,
    )

    with pytest.raises(WarehouseGenericError):
        client.post(
            f"orders-incoming/{warehouse_order.code}/transition",
            json={},
        )
