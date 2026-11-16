"""
End-to-end: the origin country stamped on a purchase order line can be deduced
from a warehouse item (item -> inbound warehouse order line -> country), also
after the item got moved partially / split, and is then required by a sales order.
"""

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.inbound_orders import routes as order_routes
from apps.warehouse.api.routes.outbound_orders import routes as outbound_routes
from apps.warehouse.api.routes.warehouse import routes as warehouse_routes
from apps.warehouse.core.exceptions import ApiBaseException
from apps.warehouse.core.schemas.orders import InboundOrderCreateOrUpdateSchema
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    InboundWarehouseOrderItem,
    OutboundWarehouseOrder,
    WarehouseItem,
)
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    WarehouseItemFactory,
    WarehouseLocationFactory,
)


@pytest.fixture
def order_client() -> TestClient:
    return TestClient(order_routes)


@pytest.fixture
def warehouse_client() -> TestClient:
    return TestClient(warehouse_routes)


def _buy(order_client: TestClient, supplier, lines: list[tuple]) -> str:
    """Create + submit a purchase order. `lines` = [(product, amount, country)]."""
    res = order_client.post(
        "/",
        json=InboundOrderCreateOrUpdateSchema(
            supplier_code=supplier.code,
            supplier_name=supplier.name,
            currency="CZK",
        ).model_dump(),
    )
    code = res.json()["data"]["code"]
    for product, amount, country in lines:
        res = order_client.post(
            f"/{code}/items",
            json={
                "product_code": product.code,
                "product_name": product.name,
                "amount": amount,
                "total_price": amount * 10,
                "origin_country": country,
            },
        )
        assert res.status_code == 200
    assert (
        order_client.post(f"/{code}/transition", json={"action": "next"}).status_code
        == 200
    )
    return code


def _receive(warehouse_client: TestClient, order_code: str, receiving, storage) -> str:
    res = warehouse_client.post(
        "/orders-incoming", json={"purchase_order_code": order_code}
    )
    w_code = res.json()["data"]["code"]
    res = warehouse_client.post(
        f"/orders-incoming/{w_code}/transition", json={"location_code": receiving.code}
    )
    assert res.status_code == 200
    assert (
        warehouse_client.post(
            f"/orders-incoming/{w_code}/transition", json={}
        ).status_code
        == 200
    )
    for item in InboundWarehouseOrder.objects.get(code=w_code).items.all():
        res = warehouse_client.post(
            f"/orders-incoming/{w_code}/items/{item.id}/putaway",
            json={"new_location_code": storage.code},
        )
        assert res.status_code == 200
    return w_code


def test_warehouse_item_origin_country_is_deduced_from_the_purchase_order(
    db, order_client, warehouse_client
):
    supplier = CustomerFactory(state="CN")
    cn_product, untracked_product = StockProductFactory(), StockProductFactory()
    receiving = WarehouseLocationFactory(is_putaway=True)
    storage = WarehouseLocationFactory(is_putaway=False)

    order_code = _buy(
        order_client, supplier, [(cn_product, 10, "CN"), (untracked_product, 5, None)]
    )
    w_code = _receive(warehouse_client, order_code, receiving, storage)

    # the frozen warehouse order lines carry the snapshot
    assert {
        i.stock_product_id: i.origin_country
        for i in InboundWarehouseOrderItem.objects.filter(warehouse_order__code=w_code)
    } == {cn_product.pk: "CN", untracked_product.pk: None}

    # ... and the items deduce it
    items = {
        i.stock_product_id: i
        for i in WarehouseItem.objects.filter(order_in__code=w_code)
    }
    assert items[cn_product.pk].origin_country == "CN"
    assert items[untracked_product.pk].origin_country is None

    # API exposes it
    res = warehouse_client.get(f"/items/{items[cn_product.pk].pk}")
    assert res.status_code == 200
    assert res.json()["data"]["origin_country"] == "CN"


def test_origin_country_survives_a_partial_move(db, order_client, warehouse_client):
    supplier = CustomerFactory()
    product = StockProductFactory()
    receiving = WarehouseLocationFactory(is_putaway=True)
    storage = WarehouseLocationFactory(is_putaway=False)
    other = WarehouseLocationFactory(is_putaway=False)
    w_code = _receive(
        warehouse_client,
        _buy(order_client, supplier, [(product, 10, "VN")]),
        receiving,
        storage,
    )
    item = WarehouseItem.objects.get(order_in__code=w_code)

    res = warehouse_client.post(
        "movement",
        json={"item_id": item.pk, "location_to_code": other.code, "amount": 4},
    )
    assert res.status_code == 200, res.json()

    assert WarehouseItem.objects.filter(stock_product=product).count() == 2
    assert {
        i.origin_country for i in WarehouseItem.objects.filter(stock_product=product)
    } == {"VN"}


def test_item_without_a_source_line_has_no_origin_country(db):
    assert WarehouseItemFactory.it(source_order_item=None).origin_country is None


def test_sales_order_for_customer_requiring_country_full_flow(db, warehouse_client):
    customer = CustomerFactory(requires_origin_country=True)
    product = StockProductFactory()
    storage = WarehouseLocationFactory(is_putaway=False)
    WarehouseItemFactory.it(stock_product=product, amount=100, location=storage)
    client = TestClient(outbound_routes)

    res = client.post(
        "/",
        json={
            "currency": "CZK",
            "customer_code": customer.code,
            "customer_name": customer.name,
        },
    )
    op = res.json()["data"]["code"]
    base = {
        "product_code": product.code,
        "product_name": product.name,
        "amount": 5,
        "total_price": 50,
    }
    assert client.post(f"/{op}/items", json=base).status_code == 200
    assert (
        client.post(
            f"/{op}/items", json={**base, "required_origin_country": "CZ"}
        ).status_code
        == 200
    )

    with pytest.raises(ApiBaseException):
        client.post(f"/{op}/transition", json={"action": "next"})

    res = client.post(f"/{op}/origin-country", json={"country": "DE"})
    assert res.status_code == 200
    assert client.post(f"/{op}/transition", json={"action": "next"}).status_code == 200

    w_order = OutboundWarehouseOrder.objects.get(order__code=op)
    assert {r.required_origin_country for r in w_order.order_items.all()} == {"DE"}

    # picking is NOT validated against the country (the stock has none)
    res = warehouse_client.get(f"/orders-outgoing/{w_order.code}")
    assert res.status_code == 200
    assert {
        i["required_origin_country"] for i in res.json()["data"]["order_items"]
    } == {"DE"}
    requirement = w_order.order_items.first()
    res = warehouse_client.post(
        f"/orders-outgoing/{w_order.code}/order-items/{requirement.pk}/assign",
        json={
            "warehouse_item_id": WarehouseItem.objects.get(stock_product=product).pk,
            "amount": 5,
        },
    )
    assert res.status_code == 200
