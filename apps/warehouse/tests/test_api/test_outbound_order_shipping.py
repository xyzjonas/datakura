from decimal import Decimal

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.outbound_orders import routes
from apps.warehouse.models.audit import AuditLog
from apps.warehouse.models.shipping import OutboundOrderShipping, ShippingType
from apps.warehouse.tests.factories.customer import ContactPersonFactory
from apps.warehouse.tests.factories.order import (
    OutboundOrderFactory,
    OutboundOrderItemFactory,
    OutboundOrderShippingFactory,
    ShippingTypeFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory


def _payload(shipping_type: ShippingType, **overrides) -> dict:
    return {
        "shipping_type_id": shipping_type.id,
        "name": "Svitlana Zherstenko",
        "state": "CZ",
        "city": "LITOVEL",
        "street": "Tři Dvory 98",
        "postal_code": "78401",
        "email": "zherstenko@brazzale.cz",
        "phone": "+420 770 181 044",
        **overrides,
    }


def _order_update_payload(order, **overrides) -> dict:
    return {
        "currency": order.currency,
        "customer_code": order.customer.code,
        "customer_name": order.customer.name,
        **overrides,
    }


def test_order_without_shipping_has_none(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()

    data = client.get(f"/{order.code}").json()["data"]

    assert data["shipping"] is None


def test_upsert_creates_then_updates_shipping(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    ppl = ShippingTypeFactory.it(name="Balík PPL")
    post = ShippingTypeFactory.it(name="Pošta")

    created = client.put(
        f"/{order.code}/shipping",
        json=_payload(
            ppl, width=10.5, height=20, depth=30, price=100, price_with_vat=121
        ),
    )

    assert created.status_code == 200
    shipping = created.json()["data"]["shipping"]
    assert shipping["shipping_type"]["name"] == "Balík PPL"
    assert shipping["width"] == 10.5
    assert shipping["price_with_vat"] == 121
    assert shipping["city"] == "LITOVEL"

    updated = client.put(
        f"/{order.code}/shipping",
        json=_payload(post, package_number="123456", city="Olomouc"),
    )

    shipping = updated.json()["data"]["shipping"]
    assert shipping["shipping_type"]["name"] == "Pošta"
    assert shipping["package_number"] == "123456"
    assert shipping["city"] == "Olomouc"
    assert shipping["width"] is None
    assert OutboundOrderShipping.objects.count() == 1


def test_upsert_writes_audit_entry(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()

    client.put(f"/{order.code}/shipping", json=_payload(ShippingTypeFactory.it()))

    assert AuditLog.objects.filter(reason__contains="dopravě").count() == 1


def test_upsert_requires_shipping_type(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()

    res = client.put(f"/{order.code}/shipping", json={"name": "x"})

    assert res.status_code == 422
    assert not OutboundOrderShipping.objects.exists()


@pytest.mark.parametrize(
    "field", ["width", "height", "depth", "price", "price_with_vat"]
)
def test_upsert_rejects_negative_numbers(db, field: str) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()

    res = client.put(
        f"/{order.code}/shipping",
        json=_payload(ShippingTypeFactory.it(), **{field: -1}),
    )

    assert res.status_code == 422


def test_upsert_with_missing_shipping_type_or_order(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    ppl = ShippingTypeFactory.it()

    with pytest.raises(ShippingType.DoesNotExist):
        client.put(
            f"/{order.code}/shipping", json=_payload(ppl, shipping_type_id=999_999)
        )
    with pytest.raises(OutboundOrderFactory._meta.model.DoesNotExist):
        client.put("/UNKNOWN/shipping", json=_payload(ppl))


def test_delete_shipping(db) -> None:
    client = TestClient(routes)
    shipping = OutboundOrderShippingFactory.it()

    res = client.delete(f"/{shipping.order.code}/shipping")

    assert res.status_code == 200
    assert res.json()["data"]["shipping"] is None
    assert not OutboundOrderShipping.objects.exists()
    # the shipping type itself stays
    assert ShippingType.objects.filter(pk=shipping.shipping_type.pk).exists()


def test_delete_shipping_is_idempotent(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()

    res = client.delete(f"/{order.code}/shipping")

    assert res.status_code == 200
    assert res.json()["data"]["shipping"] is None


@pytest.mark.parametrize(
    ("amounts_and_weights", "expected"),
    [
        ([], 0),
        ([("2", "1.50")], 3),
        ([("2", "1.50"), ("0.5", "10.00"), ("3", "0")], 8),
    ],
)
def test_total_weight_derived_from_items(
    db, amounts_and_weights: list[tuple[str, str]], expected: float
) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    for index, (amount, weight) in enumerate(amounts_and_weights):
        OutboundOrderItemFactory.it(
            order=order,
            index=index,
            amount=Decimal(amount),
            stock_product=StockProductFactory.it(unit_weight=Decimal(weight)),
        )

    data = client.get(f"/{order.code}").json()["data"]

    assert data["total_weight"] == expected


def test_changing_contact_rewrites_shipping_address(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    first, second = (ContactPersonFactory.it(customer=order.customer) for _ in range(2))
    ppl = ShippingTypeFactory.it()
    client.put(f"/{order.code}", json=_order_update_payload(order, contact_id=first.id))
    client.put(
        f"/{order.code}/shipping",
        json=_payload(ppl, package_number="ABC", name="Overridden", width=5),
    )

    res = client.put(
        f"/{order.code}", json=_order_update_payload(order, contact_id=second.id)
    )

    shipping = res.json()["data"]["shipping"]
    assert shipping["name"] == second.get_full_name()
    assert shipping["city"] == second.city
    assert shipping["street"] == second.street
    assert shipping["postal_code"] == second.postal_code
    assert shipping["email"] == second.email
    assert shipping["phone"] == second.phone
    # transit data are untouched
    assert shipping["shipping_type"]["id"] == ppl.id
    assert shipping["package_number"] == "ABC"
    assert shipping["width"] == 5
    # persisted, not just returned
    assert OutboundOrderShipping.objects.get().name == second.get_full_name()


def test_contact_without_address_falls_back_to_blank_strings(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    contact = ContactPersonFactory.it(
        customer=order.customer, street=None, city=None, postal_code=None, state=None
    )
    OutboundOrderShippingFactory.it(order=order)

    res = client.put(
        f"/{order.code}", json=_order_update_payload(order, contact_id=contact.id)
    )

    shipping = res.json()["data"]["shipping"]
    assert shipping["street"] == ""
    assert shipping["city"] == ""
    assert shipping["state"] == order.customer.state


def test_unchanged_contact_keeps_overridden_address(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    contact = ContactPersonFactory.it(customer=order.customer)
    client.put(
        f"/{order.code}", json=_order_update_payload(order, contact_id=contact.id)
    )
    client.put(
        f"/{order.code}/shipping",
        json=_payload(ShippingTypeFactory.it(), city="Manual city"),
    )

    res = client.put(
        f"/{order.code}",
        json=_order_update_payload(order, contact_id=contact.id, note="changed"),
    )

    assert res.json()["data"]["shipping"]["city"] == "Manual city"


def test_removing_contact_keeps_shipping_address(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    contact = ContactPersonFactory.it(customer=order.customer)
    client.put(
        f"/{order.code}", json=_order_update_payload(order, contact_id=contact.id)
    )
    client.put(f"/{order.code}/shipping", json=_payload(ShippingTypeFactory.it()))

    res = client.put(f"/{order.code}", json=_order_update_payload(order))

    assert res.json()["data"]["shipping"]["city"] == "LITOVEL"


def test_contact_change_without_shipping_does_not_create_one(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    contact = ContactPersonFactory.it(customer=order.customer)

    res = client.put(
        f"/{order.code}", json=_order_update_payload(order, contact_id=contact.id)
    )

    assert res.json()["data"]["shipping"] is None
    assert not OutboundOrderShipping.objects.exists()
