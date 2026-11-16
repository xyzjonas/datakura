import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from ninja.testing import TestClient

from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.api.routes.outbound_orders import routes as order_routes
from apps.warehouse.api.routes.product import routes
from apps.warehouse.models.orders import OutboundOrderState
from apps.warehouse.models.product import CustomerProductCode
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.order import (
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import (
    CustomerProductCodeFactory,
    StockProductFactory,
)


def _item_body(product, **extra) -> dict:
    return {
        "product_code": product.code,
        "product_name": product.name,
        "amount": 2,
        "total_price": 10,
        **extra,
    }


# --- model ---------------------------------------------------------------------


def test_product_can_have_one_code_per_customer(db) -> None:
    entry = CustomerProductCodeFactory.it()
    with pytest.raises(IntegrityError), transaction.atomic():
        CustomerProductCodeFactory.it(product=entry.product, customer=entry.customer)


def test_same_product_may_have_codes_for_different_customers(db) -> None:
    product = StockProductFactory.it()
    CustomerProductCodeFactory.it(product=product, code="X-1")
    CustomerProductCodeFactory.it(product=product, code="X-1")
    assert product.customer_codes.count() == 2


def test_empty_code_rejected_by_db(db) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        CustomerProductCodeFactory.it(code="")


# --- product CRUD ----------------------------------------------------------------


def test_list_customer_codes(db) -> None:
    client = TestClient(routes)
    entry = CustomerProductCodeFactory.it(code="ABC")
    CustomerProductCodeFactory.it()  # other product - not listed

    res = client.get(f"/{entry.product.code}/customer-codes")

    assert res.status_code == 200
    data = res.json()["data"]
    assert [d["code"] for d in data] == ["ABC"]
    assert data[0]["customer"]["code"] == entry.customer.code


def test_list_customer_codes_unknown_product_404(db) -> None:
    with pytest.raises(ObjectDoesNotExist):
        TestClient(routes).get("/nope/customer-codes")


def test_upsert_creates_then_replaces_code(db) -> None:
    client = TestClient(routes)
    product = StockProductFactory.it()
    customer = CustomerFactory.it()
    url = f"/{product.code}/customer-codes"

    first = client.post(url, json={"customer_code": customer.code, "code": " A-1 "})
    second = client.post(url, json={"customer_code": customer.code, "code": "A-2"})

    assert first.status_code == second.status_code == 200
    assert first.json()["data"]["code"] == "A-1"  # trimmed
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    assert list(product.customer_codes.values_list("code", flat=True)) == ["A-2"]


@pytest.mark.parametrize("code", ["", "   ", "x" * 101])
def test_upsert_rejects_invalid_code(db, code) -> None:
    product = StockProductFactory.it()
    customer = CustomerFactory.it()
    res = TestClient(routes).post(
        f"/{product.code}/customer-codes",
        json={"customer_code": customer.code, "code": code},
    )
    assert res.status_code == 422
    assert not CustomerProductCode.objects.exists()


def test_upsert_unknown_customer_404(db) -> None:
    product = StockProductFactory.it()
    with pytest.raises(ObjectDoesNotExist):
        TestClient(routes).post(
            f"/{product.code}/customer-codes",
            json={"customer_code": "nope", "code": "A"},
        )


def test_update_code(db) -> None:
    entry = CustomerProductCodeFactory.it(code="OLD")
    res = TestClient(routes).patch(
        f"/{entry.product.code}/customer-codes/{entry.id}", json={"code": "NEW"}
    )
    assert res.status_code == 200
    entry.refresh_from_db()
    assert entry.code == "NEW"


def test_update_code_of_other_product_404(db) -> None:
    entry = CustomerProductCodeFactory.it(code="OLD")
    other = StockProductFactory.it()
    with pytest.raises(ObjectDoesNotExist):
        TestClient(routes).patch(
            f"/{other.code}/customer-codes/{entry.id}", json={"code": "NEW"}
        )
    entry.refresh_from_db()
    assert entry.code == "OLD"


def test_delete_code_returns_remaining(db) -> None:
    product = StockProductFactory.it()
    gone = CustomerProductCodeFactory.it(product=product)
    kept = CustomerProductCodeFactory.it(product=product, code="KEEP")

    res = TestClient(routes).delete(f"/{product.code}/customer-codes/{gone.id}")

    assert res.status_code == 200
    assert [d["code"] for d in res.json()["data"]] == ["KEEP"]
    assert CustomerProductCode.objects.filter(pk=kept.pk).exists()


def test_delete_code_of_other_product_404(db) -> None:
    entry = CustomerProductCodeFactory.it()
    other = StockProductFactory.it()
    with pytest.raises(ObjectDoesNotExist):
        TestClient(routes).delete(f"/{other.code}/customer-codes/{entry.id}")
    assert CustomerProductCode.objects.filter(pk=entry.pk).exists()


# --- outbound order items ----------------------------------------------------------


def test_add_item_with_code_stores_it_for_customer(db) -> None:
    client = TestClient(order_routes)
    order = OutboundOrderFactory.it()
    product = StockProductFactory.it()

    res = client.post(
        f"/{order.code}/items", json=_item_body(product, customer_product_code="C-9")
    )

    assert res.status_code == 200
    assert res.json()["data"]["customer_product_code"] is None  # flag off: not shown
    assert (
        CustomerProductCode.objects.get(product=product, customer=order.customer).code
        == "C-9"
    )


def test_add_item_shows_code_for_flagged_customer(db) -> None:
    client = TestClient(order_routes)
    order = OutboundOrderFactory.it(customer=CustomerFactory.it(requires_own_codes=True))
    product = StockProductFactory.it()

    res = client.post(
        f"/{order.code}/items", json=_item_body(product, customer_product_code="C-9")
    )

    assert res.json()["data"]["customer_product_code"] == "C-9"
    items = client.get(f"/{order.code}").json()["data"]["items"]
    assert [i["customer_product_code"] for i in items] == ["C-9"]


def test_item_without_code_keeps_existing_one(db) -> None:
    client = TestClient(order_routes)
    order = OutboundOrderFactory.it(customer=CustomerFactory.it(requires_own_codes=True))
    product = StockProductFactory.it()
    CustomerProductCodeFactory.it(product=product, customer=order.customer, code="KEEP")

    res = client.post(f"/{order.code}/items", json=_item_body(product))

    assert res.json()["data"]["customer_product_code"] == "KEEP"


def test_update_item_replaces_code(db) -> None:
    client = TestClient(order_routes)
    order = OutboundOrderFactory.it(customer=CustomerFactory.it(requires_own_codes=True))
    product = StockProductFactory.it()
    CustomerProductCodeFactory.it(product=product, customer=order.customer, code="OLD")
    OutboundOrderItemFactory(order=order, stock_product=product, index=0)

    res = client.put(
        f"/{order.code}/items/0", json=_item_body(product, customer_product_code="NEW")
    )

    assert res.status_code == 200
    assert res.json()["data"]["customer_product_code"] == "NEW"
    assert CustomerProductCode.objects.get(product=product).code == "NEW"


def test_code_too_long_rejected(db) -> None:
    order = OutboundOrderFactory.it()
    product = StockProductFactory.it()
    res = TestClient(order_routes).post(
        f"/{order.code}/items",
        json=_item_body(product, customer_product_code="x" * 101),
    )
    assert res.status_code == 422


def test_other_customers_code_not_used(db) -> None:
    client = TestClient(order_routes)
    order = OutboundOrderFactory.it(customer=CustomerFactory.it(requires_own_codes=True))
    product = StockProductFactory.it()
    CustomerProductCodeFactory.it(product=product, code="NOT-MINE")
    OutboundOrderItemFactory(order=order, stock_product=product, index=0)

    items = client.get(f"/{order.code}").json()["data"]["items"]

    assert items[0]["customer_product_code"] is None


# --- confirmation ---------------------------------------------------------------------


def test_confirm_blocked_when_item_lacks_code(db) -> None:
    client = TestClient(order_routes)
    order = OutboundOrderFactory.it(
        state=OutboundOrderState.SUBMITTED,
        customer=CustomerFactory.it(requires_own_codes=True),
    )
    with_code = StockProductFactory.it()
    without = StockProductFactory.it()
    CustomerProductCodeFactory.it(product=with_code, customer=order.customer)
    OutboundOrderItemFactory(order=order, stock_product=with_code, index=0)
    OutboundOrderItemFactory(order=order, stock_product=without, index=1)

    with pytest.raises(WarehouseItemBadRequestError) as exc:
        client.post(f"/{order.code}/transition", json={"action": "next"})

    assert without.code in str(exc.value)
    assert with_code.code not in str(exc.value)
    order.refresh_from_db()
    assert order.state == OutboundOrderState.SUBMITTED
    assert not order.warehouse_orders.exists()


def test_confirm_works_when_all_items_have_codes(db) -> None:
    client = TestClient(order_routes)
    order = OutboundOrderFactory.it(
        state=OutboundOrderState.SUBMITTED,
        customer=CustomerFactory.it(requires_own_codes=True),
    )
    product = StockProductFactory.it()
    CustomerProductCodeFactory.it(product=product, customer=order.customer)
    OutboundOrderItemFactory(order=order, stock_product=product, index=0)

    res = client.post(f"/{order.code}/transition", json={"action": "next"})

    assert res.status_code == 200


def test_confirm_ignores_missing_codes_without_flag(db) -> None:
    client = TestClient(order_routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)
    OutboundOrderItemFactory(order=order, stock_product=StockProductFactory.it(), index=0)

    res = client.post(f"/{order.code}/transition", json={"action": "next"})

    assert res.status_code == 200


def test_cancel_not_blocked_by_missing_codes(db) -> None:
    client = TestClient(order_routes)
    order = OutboundOrderFactory.it(
        state=OutboundOrderState.SUBMITTED,
        customer=CustomerFactory.it(requires_own_codes=True),
    )
    OutboundOrderItemFactory(order=order, stock_product=StockProductFactory.it(), index=0)

    res = client.post(f"/{order.code}/transition", json={"action": "cancel"})

    assert res.status_code == 200
