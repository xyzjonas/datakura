from typing import cast
from datetime import timedelta

import pytest
from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.warehouse import routes
from apps.warehouse.core.exceptions import (
    WarehouseGenericError,
    WarehouseItemNotFoundError,
)
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrderState,
    WarehouseItem,
    WarehouseMovement,
    WarehouseLocation,
)
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
)
from apps.warehouse.tests.factories.order import InboundOrderItemFactory


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
    item = cast(WarehouseItem, WarehouseItemFactory())

    res = client.get(f"items/{item.pk}")

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["id"] == item.pk
    assert data["product"]["code"] == item.stock_product.code
    assert data["location"]["code"] == item.location.code


def test_get_warehouse_item_detail_not_found(db, client) -> None:
    with pytest.raises(WarehouseItemNotFoundError):
        client.get("items/999999")


def test_get_inbound_warehouse_order_includes_movements_desc(db, client) -> None:
    order = InboundWarehouseOrderFactory.create_complete(
        state=InboundWarehouseOrderState.PENDING
    )
    item = order.items.first()
    assert item
    location_a = cast(WarehouseLocation, WarehouseLocationFactory())
    location_b = cast(WarehouseLocation, WarehouseLocationFactory())

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


def test_get_inbound_warehouse_order_includes_total_and_remaining_amount(
    db, client
) -> None:
    # order = InboundWarehouseOrderFactory.create_complete(
    #     state=InboundWarehouseOrderState.PENDING,
    #     amount=100,
    #     is_putaway=True
    # )
    # item: WarehouseItem = order.items.first()
    putaway_location = WarehouseLocationFactory(is_putaway=True)
    order = InboundWarehouseOrderFactory._(state=InboundWarehouseOrderState.PENDING)
    to_be_moved_1 = WarehouseItemFactory._(
        order_in=order, location=putaway_location, amount=10
    )
    to_be_moved_2 = WarehouseItemFactory._(
        order_in=order, location=putaway_location, amount=10
    )

    InboundOrderItemFactory(
        order=order.order, stock_product=to_be_moved_1.stock_product, amount=10
    )
    InboundOrderItemFactory(
        order=order.order, stock_product=to_be_moved_2.stock_product, amount=10
    )
    new_location = WarehouseLocationFactory._(is_putaway=False)

    res = client.get(f"orders-incoming/{order.code}")

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total_amount"] == 20.0
    assert data["remaining_amount"] == 20.0

    warehouse_service.putaway_item(to_be_moved_1.pk, order.code, new_location.code)

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
    src = WarehouseLocationFactory._()
    dst = WarehouseLocationFactory._()

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
