from typing import Any

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.outbound_orders import routes
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.models.orders import (
    OutboundCalculationItem,
    OutboundOrderItem,
    OutboundOrderState,
)
from apps.warehouse.models.warehouse import OutboundWarehouseOrder
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.order import (
    OutboundCalculationFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.api.routes.outbound_calculations import routes as calc_routes


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


def _order(requires: bool, state=OutboundOrderState.SUBMITTED):
    customer = CustomerFactory.it(requires_origin_country=requires)
    return OutboundOrderFactory.it(customer=customer, state=state)


@pytest.mark.parametrize(
    "sent, stored", [("CN", "CN"), ("de", "DE"), (None, None), ("", None)]
)
def test_add_item_stores_required_origin_country(db, client, sent, stored) -> None:
    order = _order(requires=False)

    res = client.post(
        f"/{order.code}/items", json=_payload(required_origin_country=sent)
    )

    assert res.status_code == 200
    assert res.json()["data"]["required_origin_country"] == stored
    assert OutboundOrderItem.objects.get(order=order).required_origin_country == stored


@pytest.mark.parametrize("sent", ["XX", "CZE", "UK"])
def test_add_item_rejects_invalid_country(db, client, sent) -> None:
    order = _order(requires=False)

    res = client.post(
        f"/{order.code}/items", json=_payload(required_origin_country=sent)
    )

    assert res.status_code == 422
    assert not order.items.exists()


def test_update_item_changes_and_clears_required_origin_country(db, client) -> None:
    order = _order(requires=False)
    item = OutboundOrderItemFactory.it(order=order, required_origin_country="CZ")
    payload = {
        "product_code": item.stock_product.code,
        "product_name": item.stock_product.name,
        "amount": 1,
        "total_price": 10,
    }

    res = client.put(
        f"/{order.code}/items/{item.index}",
        json={**payload, "required_origin_country": "DE"},
    )
    assert res.status_code == 200
    item.refresh_from_db()
    assert item.required_origin_country == "DE"

    res = client.put(f"/{order.code}/items/{item.index}", json=payload)
    assert res.status_code == 200
    item.refresh_from_db()
    assert item.required_origin_country is None


# --- validation when moving the order to the warehouse ---------------------------


def test_transition_blocked_when_customer_requires_country_and_item_lacks_it(
    db, client
) -> None:
    order = _order(requires=True)
    OutboundOrderItemFactory.it(order=order, required_origin_country="CZ")
    OutboundOrderItemFactory.it(order=order, required_origin_country=None)

    with pytest.raises(WarehouseItemBadRequestError, match="row\\(s\\): 2"):
        client.post(f"/{order.code}/transition", json={"action": "next"})

    order.refresh_from_db()
    assert order.state == OutboundOrderState.SUBMITTED
    assert not OutboundWarehouseOrder.objects.filter(order=order).exists()


def test_transition_lists_all_rows_missing_a_country(db, client) -> None:
    order = _order(requires=True)
    for _ in range(3):
        OutboundOrderItemFactory.it(order=order)

    with pytest.raises(WarehouseItemBadRequestError, match="row\\(s\\): 1, 2, 3"):
        client.post(f"/{order.code}/transition", json={"action": "next"})


def test_transition_passes_when_every_item_has_a_country(db, client) -> None:
    order = _order(requires=True)
    OutboundOrderItemFactory.it(order=order, required_origin_country="CZ")
    OutboundOrderItemFactory.it(order=order, required_origin_country="DE")

    res = client.post(f"/{order.code}/transition", json={"action": "next"})

    assert res.status_code == 200
    w_order = OutboundWarehouseOrder.objects.get(order=order)
    assert {r.required_origin_country for r in w_order.order_items.all()} == {
        "CZ",
        "DE",
    }


def test_transition_not_validated_for_customer_without_the_flag(db, client) -> None:
    order = _order(requires=False)
    OutboundOrderItemFactory.it(order=order, required_origin_country=None)

    res = client.post(f"/{order.code}/transition", json={"action": "next"})

    assert res.status_code == 200


def test_cancel_is_not_blocked_by_missing_country(db, client) -> None:
    order = _order(requires=True)
    OutboundOrderItemFactory.it(order=order)

    res = client.post(f"/{order.code}/transition", json={"action": "cancel"})

    assert res.status_code == 200


def test_submitted_order_can_be_edited_without_country(db, client) -> None:
    """The requirement only kicks in when the order goes to the warehouse."""
    order = _order(requires=True)

    res = client.post(f"/{order.code}/items", json=_payload())

    assert res.status_code == 200


def test_item_added_to_picking_order_needs_country(db, client) -> None:
    order = _order(requires=True, state=OutboundOrderState.PICKING)

    with pytest.raises(WarehouseItemBadRequestError):
        client.post(f"/{order.code}/items", json=_payload())
    assert not order.items.exists()

    res = client.post(
        f"/{order.code}/items", json=_payload(required_origin_country="CZ")
    )
    assert res.status_code == 200


def test_item_update_in_picking_order_cannot_drop_country(db, client) -> None:
    order = _order(requires=True, state=OutboundOrderState.PICKING)
    item = OutboundOrderItemFactory.it(order=order, required_origin_country="CZ")

    with pytest.raises(WarehouseItemBadRequestError):
        client.put(
            f"/{order.code}/items/{item.index}",
            json={
                "product_code": item.stock_product.code,
                "product_name": item.stock_product.name,
                "amount": 1,
                "total_price": 10,
            },
        )
    item.refresh_from_db()
    assert item.required_origin_country == "CZ"


# --- bulk --------------------------------------------------------------------------


def test_bulk_set_required_origin_country(db, client) -> None:
    order = _order(requires=True)
    other = _order(requires=True)
    for c in (None, "CZ", "DE"):
        OutboundOrderItemFactory.it(order=order, required_origin_country=c)
    untouched = OutboundOrderItemFactory.it(order=other, required_origin_country="SK")

    res = client.post(f"/{order.code}/origin-country", json={"country": "it"})

    assert res.status_code == 200
    assert [i["required_origin_country"] for i in res.json()["data"]["items"]] == [
        "IT"
    ] * 3
    untouched.refresh_from_db()
    assert untouched.required_origin_country == "SK"

    # ... which makes the order passable
    res = client.post(f"/{order.code}/transition", json={"action": "next"})
    assert res.status_code == 200


def test_bulk_clear_in_submitted_order(db, client) -> None:
    order = _order(requires=True)
    OutboundOrderItemFactory.it(order=order, required_origin_country="CZ")

    res = client.post(f"/{order.code}/origin-country", json={"country": None})

    assert res.status_code == 200
    assert order.items.get().required_origin_country is None


def test_bulk_clear_refused_for_picking_order_of_requiring_customer(db, client) -> None:
    order = _order(requires=True, state=OutboundOrderState.PICKING)
    item = OutboundOrderItemFactory.it(order=order, required_origin_country="CZ")

    with pytest.raises(WarehouseItemBadRequestError):
        client.post(f"/{order.code}/origin-country", json={"country": None})

    item.refresh_from_db()
    assert item.required_origin_country == "CZ"


def test_bulk_set_on_picking_order_updates_warehouse_requirements(db, client) -> None:
    order = _order(requires=True)
    OutboundOrderItemFactory.it(order=order, required_origin_country="CZ")
    assert (
        client.post(f"/{order.code}/transition", json={"action": "next"}).status_code
        == 200
    )

    res = client.post(f"/{order.code}/origin-country", json={"country": "PL"})

    assert res.status_code == 200
    w_order = OutboundWarehouseOrder.objects.get(order=order)
    assert [r.required_origin_country for r in w_order.order_items.all()] == ["PL"]
    item = w_order.order_items.get()
    # the requirement is informative only - no picking validation
    assert item.warehouse_item is None


def test_bulk_set_invalid_country(db, client) -> None:
    order = _order(requires=False)
    item = OutboundOrderItemFactory.it(order=order, required_origin_country="CZ")

    res = client.post(f"/{order.code}/origin-country", json={"country": "XX"})

    assert res.status_code == 422
    item.refresh_from_db()
    assert item.required_origin_country == "CZ"


def test_bulk_set_refused_for_cancelled_order(db, client) -> None:
    order = _order(requires=False, state=OutboundOrderState.CANCELLED)
    OutboundOrderItemFactory.it(order=order)

    with pytest.raises(WarehouseItemBadRequestError):
        client.post(f"/{order.code}/origin-country", json={"country": "CZ"})


# --- carried over by duplicate / calculation flip ---------------------------------


def test_duplicate_order_keeps_required_origin_country(db, client) -> None:
    order = _order(requires=False)
    OutboundOrderItemFactory.it(order=order, required_origin_country="JP")

    res = client.post(f"/{order.code}/duplicate")

    assert res.status_code == 200
    assert [i["required_origin_country"] for i in res.json()["data"]["items"]] == ["JP"]


def test_calculation_flip_keeps_required_origin_country(db) -> None:
    calc_client = TestClient(calc_routes)
    calculation = OutboundCalculationFactory.it(
        customer=CustomerFactory.it(requires_origin_country=True)
    )
    OutboundCalculationItem.objects.create(
        calculation=calculation,
        stock_product=StockProductFactory.it(),
        amount=1,
        index=0,
        required_origin_country="KR",
    )

    res = calc_client.post(f"/{calculation.code}/create-order")

    assert res.status_code == 200
    order_item = OutboundOrderItem.objects.get(order__code=res.json()["data"]["code"])
    assert order_item.required_origin_country == "KR"


# --- calculations (nabídky) ----------------------------------------------------------


def test_calculation_bulk_set_and_clear_required_origin_country(db) -> None:
    calc_client = TestClient(calc_routes)
    calculation = OutboundCalculationFactory.it()
    for c in (None, "CZ"):
        OutboundCalculationItem.objects.create(
            calculation=calculation,
            stock_product=StockProductFactory.it(),
            amount=1,
            index=OutboundCalculationItem.objects.filter(
                calculation=calculation
            ).count(),
            required_origin_country=c,
        )

    res = calc_client.post(
        f"/{calculation.code}/origin-country", json={"country": "us"}
    )
    assert res.status_code == 200
    assert [i["required_origin_country"] for i in res.json()["data"]["items"]] == [
        "US",
        "US",
    ]

    res = calc_client.post(
        f"/{calculation.code}/origin-country", json={"country": None}
    )
    assert res.status_code == 200
    assert [i["required_origin_country"] for i in res.json()["data"]["items"]] == [
        None,
        None,
    ]


def test_calculation_bulk_set_rejects_invalid_country(db) -> None:
    calc_client = TestClient(calc_routes)
    calculation = OutboundCalculationFactory.it()

    res = calc_client.post(
        f"/{calculation.code}/origin-country", json={"country": "ZZ"}
    )

    assert res.status_code == 422


def test_order_embeds_customer_flag_and_country(db, client) -> None:
    customer = CustomerFactory.it(requires_origin_country=True, state="DE")
    order = OutboundOrderFactory.it(customer=customer)

    res = client.get(f"/{order.code}")

    assert res.status_code == 200
    assert res.json()["data"]["customer"]["requires_origin_country"] is True
    assert res.json()["data"]["customer"]["state"] == "DE"
