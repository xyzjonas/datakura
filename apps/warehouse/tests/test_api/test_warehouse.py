from typing import cast

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.warehouse import routes
from apps.warehouse.core.exceptions import WarehouseGenericError
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import InboundWarehouseOrderState, WarehouseItem
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def test_putaway_item(db, client) -> None:
    order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)
    item = cast(WarehouseItem, WarehouseItemFactory(order_in=order))
    new_location = WarehouseLocationFactory()

    res = client.post(
        f"orders-incoming/{order.code}/items/{item.code}/putaway",
        json={"new_location_code": new_location.code},
    )

    assert res.status_code == 200
    item.refresh_from_db()
    assert item.location == new_location


def test_putaway_item_invalid_state(db, client) -> None:
    order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.DRAFT)
    item = WarehouseItemFactory(order_in=order)
    new_location = WarehouseLocationFactory()

    with pytest.raises(WarehouseGenericError):
        client.post(
            f"orders-incoming/{order.code}/items/{item.code}/putaway",
            json={"new_location_code": new_location.code},
        )


def test_putaway_item_merge(db, client) -> None:
    order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)
    item_to_move = cast(WarehouseItem, WarehouseItemFactory(order_in=order))
    original_amount = item_to_move.amount

    new_location = WarehouseLocationFactory()
    existing_item = cast(
        WarehouseItem,
        WarehouseItemFactory(
            code=item_to_move.code,
            location=new_location,
            stock_product=item_to_move.stock_product,
        ),
    )
    existing_amount = existing_item.amount

    res = client.post(
        f"orders-incoming/{order.code}/items/{item_to_move.code}/putaway",
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
