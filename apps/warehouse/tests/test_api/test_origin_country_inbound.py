from typing import Any

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.customer import routes as customer_routes
from apps.warehouse.api.routes.inbound_orders import routes
from apps.warehouse.core.exceptions import WarehouseOrderNotEditableError
from apps.warehouse.models.orders import InboundOrderItem, InboundOrderState
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def _payload(**extra: Any) -> dict[str, Any]:
    product = StockProductFactory.it()
    return {
        "product_code": product.code,
        "product_name": product.name,
        "amount": 2,
        "total_price": 20,
        **extra,
    }


@pytest.mark.parametrize(
    "sent, stored",
    [
        ("CN", "CN"),
        ("cn", "CN"),
        (" de ", "DE"),
        (None, None),
        ("", None),
    ],
)
def test_add_item_stores_origin_country(db, client, sent, stored) -> None:
    order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)

    res = client.post(f"/{order.code}/items", json=_payload(origin_country=sent))

    assert res.status_code == 200
    assert res.json()["data"]["origin_country"] == stored
    assert InboundOrderItem.objects.get(order=order).origin_country == stored


def test_add_item_without_origin_country_defaults_to_null(db, client) -> None:
    order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)

    res = client.post(f"/{order.code}/items", json=_payload())

    assert res.status_code == 200
    assert res.json()["data"]["origin_country"] is None


@pytest.mark.parametrize("sent", ["XX", "CZE", "C", "UK", "12"])
def test_add_item_rejects_invalid_origin_country(db, client, sent) -> None:
    order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)

    res = client.post(f"/{order.code}/items", json=_payload(origin_country=sent))

    assert res.status_code == 422
    assert not order.items.exists()


def test_update_item_changes_and_clears_origin_country(db, client) -> None:
    order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)
    item = InboundOrderItemFactory.it(order=order, origin_country="CZ")
    payload = {
        "product_code": item.stock_product.code,
        "product_name": item.stock_product.name,
        "amount": 1,
        "total_price": 10,
    }

    res = client.put(
        f"/{order.code}/items/{item.index}", json={**payload, "origin_country": "VN"}
    )
    assert res.status_code == 200
    item.refresh_from_db()
    assert item.origin_country == "VN"

    res = client.put(f"/{order.code}/items/{item.index}", json=payload)
    assert res.status_code == 200
    item.refresh_from_db()
    assert item.origin_country is None


def test_bulk_set_origin_country_hits_all_items(db, client) -> None:
    order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)
    other_order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)
    items = [
        InboundOrderItemFactory.it(order=order, origin_country=c)
        for c in (None, "CZ", "DE")
    ]
    untouched = InboundOrderItemFactory.it(order=other_order, origin_country="SK")

    res = client.post(f"/{order.code}/origin-country", json={"country": "pl"})

    assert res.status_code == 200
    assert [i["origin_country"] for i in res.json()["data"]["items"]] == ["PL"] * 3
    for item in items:
        item.refresh_from_db()
        assert item.origin_country == "PL"
    untouched.refresh_from_db()
    assert untouched.origin_country == "SK"


def test_bulk_clear_origin_country(db, client) -> None:
    order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)
    InboundOrderItemFactory.it(order=order, origin_country="CZ")

    res = client.post(f"/{order.code}/origin-country", json={"country": None})

    assert res.status_code == 200
    assert order.items.get().origin_country is None


def test_bulk_set_on_order_without_items_is_noop(db, client) -> None:
    order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)

    res = client.post(f"/{order.code}/origin-country", json={"country": "CZ"})

    assert res.status_code == 200
    assert res.json()["data"]["items"] == []


@pytest.mark.parametrize("country", ["XX", "CZE"])
def test_bulk_set_rejects_invalid_country(db, client, country) -> None:
    order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)
    item = InboundOrderItemFactory.it(order=order, origin_country="CZ")

    res = client.post(f"/{order.code}/origin-country", json={"country": country})

    assert res.status_code == 422
    item.refresh_from_db()
    assert item.origin_country == "CZ"


def test_bulk_set_is_refused_once_order_is_locked(db, client) -> None:
    order = InboundOrderFactory.it(state=InboundOrderState.COMPLETED)
    item = InboundOrderItemFactory.it(order=order, origin_country="CZ")

    with pytest.raises(WarehouseOrderNotEditableError):
        client.post(f"/{order.code}/origin-country", json={"country": "DE"})

    item.refresh_from_db()
    assert item.origin_country == "CZ"


def test_duplicate_inbound_order_keeps_origin_country(db, client) -> None:
    order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)
    InboundOrderItemFactory.it(order=order, origin_country="JP")

    res = client.post(f"/{order.code}/duplicate")

    assert res.status_code == 200
    assert [i["origin_country"] for i in res.json()["data"]["items"]] == ["JP"]


def test_customer_requires_origin_country_flag_roundtrip(db) -> None:
    client = TestClient(customer_routes)
    customer = CustomerFactory.it()
    assert customer.requires_origin_country is False

    body = {
        "name": customer.name,
        "code": customer.code,
        "customer_type": customer.customer_type,
        "price_type": customer.price_type,
        "customer_group_code": customer.customer_group.code,
        "state": "VN",
        "requires_origin_country": True,
    }
    res = client.put(f"/{customer.code}", json=body)

    assert res.status_code == 200
    assert res.json()["data"]["requires_origin_country"] is True
    assert res.json()["data"]["state"] == "VN"
    customer.refresh_from_db()
    assert customer.requires_origin_country is True
