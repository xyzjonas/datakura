from decimal import Decimal

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.outbound_calculations import routes
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.models.orders import (
    OutboundCalculation,
    OutboundCalculationItem,
    OutboundCalculationState,
    OutboundOrder,
    OutboundOrderState,
)
from apps.warehouse.models.warehouse import OutboundWarehouseOrder
from apps.warehouse.tests.factories.customer import (
    ContactPersonFactory,
    CustomerFactory,
)
from apps.warehouse.tests.factories.order import (
    OutboundCalculationFactory,
    OutboundCalculationItemFactory,
    OutboundOrderFactory,
)
from apps.warehouse.tests.factories.packaging import PackageTypeFactory
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.settings import GlobalSettingsFactory


def _payload(customer, **overrides) -> dict:
    return {
        "currency": "CZK",
        "customer_code": customer.code,
        "customer_name": customer.name,
        **overrides,
    }


def _item_payload(product, **overrides) -> dict:
    return {
        "product_code": product.code,
        "product_name": product.name,
        "amount": 2,
        "total_price": 100,
        **overrides,
    }


def _codes(res) -> list[str]:
    return [c["code"] for c in res.json()["data"]]


def _calculation_with_items(n_items: int = 2, **kwargs) -> OutboundCalculation:
    calculation = OutboundCalculationFactory.it(**kwargs)
    for _ in range(n_items):
        OutboundCalculationItemFactory(calculation=calculation)
    return calculation


# --- create / read / update --- #


def test_create_calculation_is_open_with_k_code(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()

    res = client.post("", json=_payload(customer, description="offer", note="n"))

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["code"].startswith("K")
    assert data["state"] == "open"
    assert data["order_code"] is None
    assert data["customer"]["code"] == customer.code
    assert data["items"] == []
    calculation = OutboundCalculation.objects.get(code=data["code"])
    assert calculation.description == "offer"
    assert not OutboundOrder.objects.exists()
    assert (
        AuditLog.objects.for_object(calculation)
        .filter(action=AuditAction.CREATE)
        .exists()
    )


def test_create_calculations_get_consecutive_codes(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()

    first = client.post("", json=_payload(customer)).json()["data"]["code"]
    second = client.post("", json=_payload(customer)).json()["data"]["code"]

    assert first[:-4] == second[:-4]
    assert int(second[-4:]) == int(first[-4:]) + 1


def test_create_calculation_unknown_customer_fails(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory.build()

    with pytest.raises(Exception, match="does not exist"):
        client.post("", json=_payload(customer))

    assert not OutboundCalculation.objects.exists()


@pytest.mark.parametrize("contact_kind", ["other_customer", "deleted", "missing"])
def test_calculation_rejects_invalid_contact(db, contact_kind: str) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()
    contact_id = {
        "other_customer": lambda: ContactPersonFactory.it().id,
        "deleted": lambda: (
            ContactPersonFactory.it(customer=customer, is_deleted=True).id
        ),
        "missing": lambda: 999_999,
    }[contact_kind]()

    with pytest.raises(WarehouseItemBadRequestError, match="does not belong"):
        client.post("", json=_payload(customer, contact_id=contact_id))

    assert not OutboundCalculation.objects.exists()


def test_create_update_and_clear_calculation_contact(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()
    contact = ContactPersonFactory.it(customer=customer)

    data = client.post("", json=_payload(customer, contact_id=contact.id)).json()[
        "data"
    ]
    assert data["contact"]["id"] == contact.id

    cleared = client.put(f"/{data['code']}", json=_payload(customer)).json()["data"]
    assert cleared["contact"] is None


def test_get_calculation(db) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(2)

    res = client.get(f"/{calculation.code}")

    data = res.json()["data"]
    assert data["code"] == calculation.code
    assert [i["index"] for i in data["items"]] == [0, 1]
    assert all(i["pricing_details"] is not None for i in data["items"])


@pytest.mark.parametrize("kind", ["missing", "deleted"])
def test_get_calculation_not_found(db, kind: str) -> None:
    client = TestClient(routes)
    OutboundCalculationFactory.it(code="K-DELETED", is_deleted=True)
    code = "K-DELETED" if kind == "deleted" else "K-NOPE"

    with pytest.raises(OutboundCalculation.DoesNotExist):
        client.get(f"/{code}")


def test_update_calculation_records_audit_diff(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it(note="old")

    res = client.put(
        f"/{calculation.code}",
        json=_payload(calculation.customer, note="new", external_code="EXT-1"),
    )

    assert res.status_code == 200
    calculation.refresh_from_db()
    assert (calculation.note, calculation.external_code) == ("new", "EXT-1")
    log = (
        AuditLog.objects.for_object(calculation).filter(action=AuditAction.UPDATE).get()
    )
    assert log.changes["note"] == {"old": "old", "new": "new"}


def test_update_closed_calculation_rejected(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it(state=OutboundCalculationState.CLOSED)

    with pytest.raises(WarehouseItemBadRequestError, match="closed"):
        client.put(f"/{calculation.code}", json=_payload(calculation.customer))


def test_update_deleted_calculation_not_found(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it(is_deleted=True)

    with pytest.raises(OutboundCalculation.DoesNotExist):
        client.put(f"/{calculation.code}", json=_payload(calculation.customer))


# --- listing --- #


def test_list_hides_closed_and_deleted_by_default(db) -> None:
    client = TestClient(routes)
    open_calc = OutboundCalculationFactory.it()
    closed = OutboundCalculationFactory.it(state=OutboundCalculationState.CLOSED)
    OutboundCalculationFactory.it(is_deleted=True)

    assert _codes(client.get("/")) == [open_calc.code]
    assert set(_codes(client.get("/?include_all=true"))) == {
        open_calc.code,
        closed.code,
    }


def test_list_never_includes_deleted_even_when_searched(db) -> None:
    client = TestClient(routes)
    deleted = OutboundCalculationFactory.it(is_deleted=True)

    assert _codes(client.get(f"/?search_term={deleted.code}&include_all=true")) == []


def test_search_matches_closed_calculation_by_code_customer_and_order(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    closed = OutboundCalculationFactory.it(
        code="K2026100001",
        state=OutboundCalculationState.CLOSED,
        order=order,
        customer=CustomerFactory(name="Zeta Corp"),
    )
    OutboundCalculationFactory.it(code="K2026100002")

    assert _codes(client.get("/?search_term=K2026100001")) == [closed.code]
    assert _codes(client.get("/?search_term=zeta")) == [closed.code]
    assert _codes(client.get(f"/?search_term={order.code}")) == [closed.code]


def test_list_filters_by_customer_and_product(db) -> None:
    client = TestClient(routes)
    product = StockProductFactory()
    mine = _calculation_with_items(0)
    OutboundCalculationItemFactory(calculation=mine, stock_product=product)
    OutboundCalculationItemFactory(calculation=mine, stock_product=product, index=1)
    other = _calculation_with_items(1)

    assert _codes(client.get(f"/?customer_code={mine.customer.code}")) == [mine.code]
    # two matching items must not duplicate the calculation
    assert _codes(client.get(f"/?stock_product_code={product.code}")) == [mine.code]
    assert other.code in _codes(client.get("/"))


def test_list_is_paginated(db) -> None:
    client = TestClient(routes)
    for _ in range(3):
        OutboundCalculationFactory.it()

    res = client.get("/?page=1&page_size=2").json()

    assert res["count"] == 3
    assert len(res["data"]) == 2
    assert (res["next"], res["previous"]) == (2, None)


# --- items --- #


def test_add_items_get_sequential_indices_and_unit_price(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it()
    product = StockProductFactory()

    first = client.post(
        f"/{calculation.code}/items", json=_item_payload(product, amount=4)
    )
    second = client.post(f"/{calculation.code}/items", json=_item_payload(product))

    assert first.json()["data"]["index"] == 0
    assert first.json()["data"]["unit_price"] == 25.0
    assert first.json()["data"]["pricing_details"] is not None
    assert second.json()["data"]["index"] == 1
    assert calculation.items.count() == 2


def test_add_item_applies_minimum_item_value(db) -> None:
    client = TestClient(routes)
    GlobalSettingsFactory(minimum_item_value=Decimal("50"))
    calculation = OutboundCalculationFactory.it()

    res = client.post(
        f"/{calculation.code}/items",
        json=_item_payload(StockProductFactory(), amount=1, total_price=10),
    )

    assert res.json()["data"]["total_price"] == 50.0


def test_add_item_with_unfitting_package_rejected(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it()
    product = StockProductFactory()
    package = PackageTypeFactory(unit_of_measure=product.unit_of_measure, amount=5)

    with pytest.raises(WarehouseItemBadRequestError, match="does not fit package"):
        client.post(
            f"/{calculation.code}/items",
            json=_item_payload(
                product, amount=7, desired_package_type_name=package.name
            ),
        )

    assert not calculation.items.exists()


def test_add_item_with_package_that_fits(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it()
    product = StockProductFactory()
    package = PackageTypeFactory(unit_of_measure=product.unit_of_measure, amount=5)

    res = client.post(
        f"/{calculation.code}/items",
        json=_item_payload(
            product, amount=10, desired_package_type_name=package.name, note="x"
        ),
    )

    data = res.json()["data"]
    assert data["desired_package_type_name"] == package.name
    assert data["note"] == "x"


def test_add_item_with_unknown_batch_rejected(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it()

    with pytest.raises(WarehouseItemBadRequestError, match="Batch"):
        client.post(
            f"/{calculation.code}/items",
            json=_item_payload(StockProductFactory(), desired_batch_code="NOPE"),
        )


@pytest.mark.parametrize("amount", [0, -1, 1_000_000])
def test_add_item_rejects_invalid_amount(db, amount) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it()

    res = client.post(
        f"/{calculation.code}/items",
        json=_item_payload(StockProductFactory(), amount=amount),
    )

    assert res.status_code == 422
    assert not calculation.items.exists()


def test_update_item(db) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(2)

    res = client.put(
        f"/{calculation.code}/items/1",
        json=_item_payload(
            calculation.items.get(index=1).stock_product, amount=5, total_price=500
        ),
    )

    assert res.status_code == 200
    item = calculation.items.get(index=1)
    assert (item.amount, item.total_price, item.unit_price) == (5, 500, 100)


def test_update_missing_item_not_found(db) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(1)

    with pytest.raises(OutboundCalculationItem.DoesNotExist):
        client.put(
            f"/{calculation.code}/items/9",
            json=_item_payload(StockProductFactory()),
        )


def test_remove_item_compacts_indices(db) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(3)
    last = calculation.items.get(index=2)

    res = client.delete(f"/{calculation.code}/items/0")

    assert res.status_code == 200
    assert [i["index"] for i in res.json()["data"]["items"]] == [0, 1]
    assert calculation.items.get(index=1).pk == last.pk


def test_reorder_item(db) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(3)
    first = calculation.items.get(index=0)

    res = client.put(f"/{calculation.code}/items/0/reorder", json={"new_index": 2})

    assert res.status_code == 200
    first.refresh_from_db()
    assert first.index == 2


@pytest.mark.parametrize("state", [OutboundCalculationState.CLOSED])
def test_items_of_closed_calculation_are_read_only(db, state) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(1, state=state)
    product = StockProductFactory()

    with pytest.raises(WarehouseItemBadRequestError, match="closed"):
        client.post(f"/{calculation.code}/items", json=_item_payload(product))
    with pytest.raises(WarehouseItemBadRequestError, match="closed"):
        client.put(f"/{calculation.code}/items/0", json=_item_payload(product))
    with pytest.raises(WarehouseItemBadRequestError, match="closed"):
        client.delete(f"/{calculation.code}/items/0")
    with pytest.raises(WarehouseItemBadRequestError, match="closed"):
        client.put(f"/{calculation.code}/items/0/reorder", json={"new_index": 0})
    assert calculation.items.count() == 1


# --- duplicate --- #


def test_duplicate_copies_header_and_items_into_new_open_calculation(db) -> None:
    client = TestClient(routes)
    source = _calculation_with_items(
        2, note="keep me", state=OutboundCalculationState.CLOSED
    )

    res = client.post(f"/{source.code}/duplicate")

    data = res.json()["data"]
    assert data["code"] != source.code
    assert data["state"] == "open"
    assert data["order_code"] is None
    assert data["note"] == "keep me"
    assert [(i["amount"], i["unit_price"]) for i in data["items"]] == [
        (float(i.amount), float(i.unit_price)) for i in source.items.order_by("index")
    ]
    source.refresh_from_db()
    assert source.state == OutboundCalculationState.CLOSED
    assert source.items.count() == 2


def test_duplicate_deleted_calculation_not_found(db) -> None:
    client = TestClient(routes)
    source = OutboundCalculationFactory.it(is_deleted=True)

    with pytest.raises(OutboundCalculation.DoesNotExist):
        client.post(f"/{source.code}/duplicate")


# --- close / reopen --- #


def test_close_and_reopen_calculation(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it()

    closed = client.post(f"/{calculation.code}/transition", json={"action": "close"})
    assert closed.json()["data"]["state"] == "closed"

    reopened = client.post(f"/{calculation.code}/transition", json={"action": "reopen"})
    assert reopened.json()["data"]["state"] == "open"
    assert (
        AuditLog.objects.for_object(calculation)
        .filter(action=AuditAction.TRANSITION)
        .count()
        == 2
    )


def test_closing_twice_is_idempotent(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it()

    client.post(f"/{calculation.code}/transition", json={"action": "close"})
    res = client.post(f"/{calculation.code}/transition", json={"action": "close"})

    assert res.json()["data"]["state"] == "closed"
    assert (
        AuditLog.objects.for_object(calculation)
        .filter(action=AuditAction.TRANSITION)
        .count()
        == 1
    )


def test_calculation_with_order_cannot_be_reopened(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it(
        state=OutboundCalculationState.CLOSED, order=OutboundOrderFactory.it()
    )

    with pytest.raises(WarehouseItemBadRequestError, match="cannot be reopened"):
        client.post(f"/{calculation.code}/transition", json={"action": "reopen"})


@pytest.mark.parametrize("action", ["cancel", "next", ""])
def test_calculation_transition_rejects_unknown_action(db, action: str) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it()

    res = client.post(f"/{calculation.code}/transition", json={"action": action})

    assert res.status_code == 422


# --- soft delete --- #


def test_delete_is_soft_and_keeps_items_and_audit(db) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(2)

    res = client.delete(f"/{calculation.code}")

    assert res.status_code == 200
    assert res.json()["success"] is True
    calculation.refresh_from_db()
    assert calculation.is_deleted is True
    assert calculation.deleted_date is not None
    assert calculation.items.count() == 2
    assert OutboundCalculation.objects.filter(pk=calculation.pk).exists()
    assert (
        AuditLog.objects.for_object(calculation)
        .filter(action=AuditAction.DELETE)
        .exists()
    )
    assert _codes(client.get("/?include_all=true")) == []
    with pytest.raises(OutboundCalculation.DoesNotExist):
        client.get(f"/{calculation.code}")


def test_delete_twice_not_found(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it()
    client.delete(f"/{calculation.code}")

    with pytest.raises(OutboundCalculation.DoesNotExist):
        client.delete(f"/{calculation.code}")


def test_deleting_calculation_keeps_its_order(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    calculation = OutboundCalculationFactory.it(
        order=order, state=OutboundCalculationState.CLOSED
    )

    client.delete(f"/{calculation.code}")

    order.refresh_from_db()
    assert order.state == OutboundOrderState.SUBMITTED
    assert OutboundOrder.objects.filter(pk=order.pk).exists()


def test_deleted_calculation_audits_not_available(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it(is_deleted=True)

    with pytest.raises(OutboundCalculation.DoesNotExist):
        client.get(f"/{calculation.code}/audits")


def test_calculation_audits(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()
    code = client.post("", json=_payload(customer)).json()["data"]["code"]
    client.put(f"/{code}", json=_payload(customer, note="x"))

    data = client.get(f"/{code}/audits").json()["data"]

    assert [e["action"] for e in data] == [AuditAction.UPDATE, AuditAction.CREATE]


# --- flip over to an order --- #


def test_create_order_mirrors_calculation_one_to_one(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()
    contact = ContactPersonFactory.it(customer=customer)
    product = StockProductFactory()
    package = PackageTypeFactory(unit_of_measure=product.unit_of_measure, amount=2)
    calculation = OutboundCalculationFactory.it(
        customer=customer,
        contact=contact,
        currency="EUR",
        note="n",
        description="d",
        external_code="E-1",
    )
    OutboundCalculationItemFactory(
        calculation=calculation,
        stock_product=product,
        amount=4,
        unit_price=Decimal("12.5"),
        total_price=Decimal("50"),
        desired_package_type=package,
        note="item note",
    )
    OutboundCalculationItemFactory(calculation=calculation, index=1)

    res = client.post(f"/{calculation.code}/create-order")

    assert res.status_code == 200
    data = res.json()["data"]
    order = OutboundOrder.objects.get(code=data["code"])
    assert order.code.startswith("OP")
    assert order.state == OutboundOrderState.SUBMITTED
    assert data["state"] == "submitted"
    assert data["calculation_code"] == calculation.code
    for field in (
        "external_code",
        "description",
        "note",
        "currency",
        "customer",
        "supplier",
        "contact",
        "requested_delivery_date",
    ):
        assert getattr(order, field) == getattr(calculation, field), field
    order_items = list(order.items.order_by("index"))
    calc_items = list(calculation.items.order_by("index"))
    assert len(order_items) == len(calc_items) == 2
    for order_item, calc_item in zip(order_items, calc_items):
        for field in (
            "stock_product",
            "amount",
            "index",
            "unit_price",
            "total_price",
            "desired_package_type",
            "desired_batch",
            "note",
        ):
            assert getattr(order_item, field) == getattr(calc_item, field), field


def test_create_order_keeps_calculation_as_is_but_closed_and_linked(db) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(2)
    snapshot = [
        (i.stock_product_id, i.amount, i.unit_price, i.total_price, i.index)
        for i in calculation.items.order_by("index")
    ]

    order_code = client.post(f"/{calculation.code}/create-order").json()["data"]["code"]

    calculation.refresh_from_db()
    assert calculation.state == OutboundCalculationState.CLOSED
    assert calculation.order is not None and calculation.order.code == order_code
    assert not calculation.is_deleted
    assert snapshot == [
        (i.stock_product_id, i.amount, i.unit_price, i.total_price, i.index)
        for i in calculation.items.order_by("index")
    ]
    detail = client.get(f"/{calculation.code}").json()["data"]
    assert detail["state"] == "closed"
    assert detail["order_code"] == order_code


def test_order_and_calculation_are_independent_after_flip(db) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(1)
    order_code = client.post(f"/{calculation.code}/create-order").json()["data"]["code"]
    order = OutboundOrder.objects.get(code=order_code)

    order.items.all().delete()
    order.note = "changed on order"
    order.save()

    calculation.refresh_from_db()
    assert calculation.items.count() == 1
    assert calculation.note != "changed on order"


def test_create_order_does_not_create_warehouse_order(db) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(1)

    client.post(f"/{calculation.code}/create-order")

    assert not OutboundWarehouseOrder.objects.exists()


def test_create_order_does_not_reapply_minimum_item_value(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it()
    OutboundCalculationItemFactory(
        calculation=calculation, amount=1, unit_price=10, total_price=10
    )
    GlobalSettingsFactory(minimum_item_value=Decimal("50"))

    code = client.post(f"/{calculation.code}/create-order").json()["data"]["code"]

    assert OutboundOrder.objects.get(code=code).items.get().total_price == 10


def test_create_order_writes_audit_on_both_sides(db) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(1)

    order_code = client.post(f"/{calculation.code}/create-order").json()["data"]["code"]

    order = OutboundOrder.objects.get(code=order_code)
    order_log = AuditLog.objects.for_object(order).get()
    assert order_log.action == AuditAction.CREATE
    assert calculation.code in (order_log.reason or "")
    calc_logs = AuditLog.objects.for_object(calculation)
    assert calc_logs.filter(action=AuditAction.TRANSITION).exists()
    assert any(order_code in (log.reason or "") for log in calc_logs)


def test_create_order_without_items_rejected(db) -> None:
    client = TestClient(routes)
    calculation = OutboundCalculationFactory.it()

    with pytest.raises(WarehouseItemBadRequestError, match="at least one item"):
        client.post(f"/{calculation.code}/create-order")

    calculation.refresh_from_db()
    assert calculation.state == OutboundCalculationState.OPEN
    assert not OutboundOrder.objects.exists()


def test_create_order_twice_rejected_and_creates_single_order(db) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(1)
    client.post(f"/{calculation.code}/create-order")

    with pytest.raises(WarehouseItemBadRequestError, match="already has order"):
        client.post(f"/{calculation.code}/create-order")

    assert OutboundOrder.objects.count() == 1


def test_create_order_from_closed_calculation_rejected(db) -> None:
    client = TestClient(routes)
    calculation = _calculation_with_items(1, state=OutboundCalculationState.CLOSED)

    with pytest.raises(WarehouseItemBadRequestError, match="closed"):
        client.post(f"/{calculation.code}/create-order")

    assert not OutboundOrder.objects.exists()


@pytest.mark.parametrize("kind", ["missing", "deleted"])
def test_create_order_from_unavailable_calculation_not_found(db, kind: str) -> None:
    client = TestClient(routes)
    deleted = _calculation_with_items(1, is_deleted=True)
    code = deleted.code if kind == "deleted" else "K-NOPE"

    with pytest.raises(OutboundCalculation.DoesNotExist):
        client.post(f"/{code}/create-order")

    assert not OutboundOrder.objects.exists()


def test_order_created_from_calculation_is_confirmable_like_any_order(db) -> None:
    from apps.warehouse.api.routes.outbound_orders import routes as order_routes

    calculation = _calculation_with_items(1)
    order_code = (
        TestClient(routes)
        .post(f"/{calculation.code}/create-order")
        .json()["data"]["code"]
    )

    res = TestClient(order_routes).post(
        f"/{order_code}/transition", json={"action": "next"}
    )

    data = res.json()["data"]
    assert data["state"] == "picking"
    assert data["code"] == order_code
    assert len(data["warehouse_orders"]) == 1
