from decimal import Decimal

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.outbound_orders import routes
from apps.warehouse.models.audit import AuditLog
from apps.warehouse.models.shipping import (
    UNKNOWN_SHIPPING_TYPE_ID,
    OutboundOrderShipping,
    ShippingType,
)
from apps.warehouse.tests.factories.customer import (
    ContactPersonFactory,
    CustomerFactory,
)
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


def test_new_order_always_has_empty_shipping(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()

    shipping = client.get(f"/{order.code}").json()["data"]["shipping"]

    assert shipping["shipping_type"] is None
    assert shipping["package_number"] == ""
    assert shipping["width"] is None
    assert shipping["price"] is None
    assert OutboundOrderShipping.objects.filter(order=order).count() == 1


def test_order_created_via_api_has_shipping_seeded_from_contact(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()
    contact = ContactPersonFactory.it(customer=customer)

    res = client.post(
        "",
        json={
            "currency": "CZK",
            "customer_code": customer.code,
            "customer_name": customer.name,
            "contact_id": contact.id,
        },
    )

    shipping = res.json()["data"]["shipping"]
    assert shipping["name"] == contact.get_full_name()
    assert shipping["city"] == contact.city
    assert shipping["shipping_type"] is None


def test_duplicated_order_has_its_own_shipping(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()

    res = client.post(f"/{order.code}/duplicate")

    assert res.status_code == 200
    assert OutboundOrderShipping.objects.count() == 2


def test_legacy_order_without_shipping_gets_one_on_read(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    OutboundOrderShipping.objects.all().delete()

    res = client.get(f"/{order.code}")

    assert res.json()["data"]["shipping"]["shipping_type"] is None
    assert OutboundOrderShipping.objects.count() == 1


def test_upsert_updates_the_existing_shipping(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    ppl = ShippingTypeFactory.it(name="Balík PPL")
    post = ShippingTypeFactory.it(name="Pošta")

    first = client.put(
        f"/{order.code}/shipping",
        json=_payload(
            ppl, width=10.5, height=20, depth=30, price=100, price_with_vat=121
        ),
    )

    assert first.status_code == 200
    shipping = first.json()["data"]["shipping"]
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


def test_upsert_without_shipping_type_clears_it(db) -> None:
    client = TestClient(routes)
    shipping = OutboundOrderShippingFactory.it()

    res = client.put(
        f"/{shipping.order.code}/shipping",
        json={"package_number": "X1", "city": "Brno"},
    )

    assert res.status_code == 200
    data = res.json()["data"]["shipping"]
    assert data["shipping_type"] is None
    assert data["package_number"] == "X1"


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


def test_shipping_cannot_be_deleted_via_api(db) -> None:
    client = TestClient(routes)
    shipping = OutboundOrderShippingFactory.it()

    res = client.delete(f"/{shipping.order.code}/shipping")

    assert res.status_code == 405
    assert OutboundOrderShipping.objects.filter(pk=shipping.pk).exists()


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


def test_empty_shipping_uses_the_unknown_sentinel_type(db) -> None:
    order = OutboundOrderFactory.it()

    shipping = OutboundOrderShipping.objects.get(order=order)

    assert shipping.shipping_type_id == UNKNOWN_SHIPPING_TYPE_ID


def test_clearing_the_type_falls_back_to_the_sentinel(db) -> None:
    client = TestClient(routes)
    shipping = OutboundOrderShippingFactory.it(shipping_type=ShippingTypeFactory.it())

    client.put(f"/{shipping.order.code}/shipping", json={})

    shipping.refresh_from_db()
    assert shipping.shipping_type_id == UNKNOWN_SHIPPING_TYPE_ID
