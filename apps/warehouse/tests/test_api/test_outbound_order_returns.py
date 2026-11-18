"""Goods taken back from a customer ("vratka") for an order that was already sent out."""

from decimal import Decimal

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.credit_notes import routes as credit_note_routes
from apps.warehouse.api.routes.outbound_orders import routes
from apps.warehouse.api.routes.warehouse import routes as warehouse_routes
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.services.outbound_orders import outbound_orders_service
from apps.warehouse.models.audit import AuditLog
from apps.warehouse.models.orders import (
    CreditNoteState,
    CreditNoteToCustomer,
    OutboundOrder,
    OutboundOrderItem,
    OutboundOrderState,
)
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    InboundWarehouseOrderState,
    OutboundWarehouseOrderItem,
)
from apps.warehouse.tests.factories.order import (
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import (
    ProductTypeFactory,
    StockProductFactory,
)
from apps.warehouse.tests.factories.warehouse import (
    OutboundWarehouseOrderItemFactory,
    WarehouseLocationFactory,
    WarehouseOrderOutFactory,
)

RETURNABLE_STATES = [
    OutboundOrderState.SENT,
    OutboundOrderState.COMPLETED,
    OutboundOrderState.INVOICED,
    OutboundOrderState.WAITING_FOR_PAYMENT,
    OutboundOrderState.COMPLETED_PAID,
]
NOT_RETURNABLE_STATES = [
    OutboundOrderState.SUBMITTED,
    OutboundOrderState.PICKING,
    OutboundOrderState.PACKING,
    OutboundOrderState.SHIPPING,
    OutboundOrderState.CANCELLED,
]


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def _sent_order(
    state: OutboundOrderState = OutboundOrderState.SENT,
) -> tuple[OutboundOrder, OutboundOrderItem, OutboundOrderItem]:
    """Order of two rows: 10 x 20 = 200 and 4 x 50 = 200."""
    order = OutboundOrderFactory.it(state=state)
    first = OutboundOrderItemFactory.it(
        order=order, amount=Decimal("10"), unit_price=Decimal("20"), total_price=200
    )
    second = OutboundOrderItemFactory.it(
        order=order, amount=Decimal("4"), unit_price=Decimal("50"), total_price=200
    )
    return order, first, second


def _return(client: TestClient, order: OutboundOrder, *lines: tuple[int, float]):
    return client.post(
        f"/{order.code}/returns",
        json={"items": [{"item_index": i, "amount": a} for i, a in lines]},
    )


def test_return_creates_rows_receipt_and_credit_note(db, client) -> None:
    order, first, second = _sent_order()

    res = _return(client, order, (first.index, 3), (second.index, 4))

    assert res.status_code == 200
    data = res.json()["data"]
    rows = data["items"]
    assert [r["is_returned"] for r in rows] == [False, False, True, True]
    returned = rows[2]
    assert returned["returned_from_index"] == first.index
    assert returned["amount"] == 3
    assert returned["unit_price"] == 20
    assert returned["total_price"] == 60  # proportional part of the sold row
    assert returned["product"]["code"] == first.stock_product.code
    assert rows[3]["total_price"] == 200
    # sold rows are untouched, they only know how much was taken back
    assert rows[0]["amount"] == 10 and rows[0]["returned_amount"] == 3
    assert rows[1]["returned_amount"] == 4

    receipt = InboundWarehouseOrder.objects.get(return_order=order)
    assert receipt.state == InboundWarehouseOrderState.IN_TRANSIT
    assert receipt.order is None and receipt.manufacturing_order is None
    assert receipt.code.startswith("PV") and receipt.code.endswith("001")
    assert receipt.currency == order.currency
    assert [w["code"] for w in data["return_warehouse_orders"]] == [receipt.code]

    note = CreditNoteToCustomer.objects.get(order=order)
    assert note.warehouse_order == receipt
    assert note.state == CreditNoteState.DRAFT
    assert note.code.startswith("DO")
    assert sorted((i.amount, i.unit_price) for i in note.items.all()) == [
        (Decimal("3"), Decimal("20")),
        (Decimal("4"), Decimal("50")),
    ]
    assert [n["code"] for n in data["credit_notes"]] == [note.code]
    assert len(data["credit_notes"][0]["items"]) == 2

    assert AuditLog.objects.filter(object_id=order.pk, changes__receipt=receipt.code)  # type: ignore[misc]


@pytest.mark.parametrize("state", RETURNABLE_STATES)
def test_return_allowed_for_sent_out_states(db, client, state) -> None:
    order, first, _ = _sent_order(state)

    assert _return(client, order, (first.index, 1)).status_code == 200


@pytest.mark.parametrize("state", NOT_RETURNABLE_STATES)
def test_return_rejected_when_goods_were_not_sent(db, client, state) -> None:
    order, first, _ = _sent_order(state)

    with pytest.raises(WarehouseItemBadRequestError):
        _return(client, order, (first.index, 1))

    assert not InboundWarehouseOrder.objects.filter(return_order=order).exists()
    assert not CreditNoteToCustomer.objects.exists()
    assert not order.items.filter(is_returned=True).exists()


@pytest.mark.parametrize("amount", [0, -1, 1_000_000])
def test_return_rejects_invalid_amount(db, client, amount) -> None:
    order, first, _ = _sent_order()

    assert _return(client, order, (first.index, amount)).status_code == 422


def test_return_rejects_empty_selection(db, client) -> None:
    order, _, _ = _sent_order()

    res = client.post(f"/{order.code}/returns", json={"items": []})

    assert res.status_code == 422


@pytest.mark.parametrize(
    "lines",
    [
        [(0, 10.0001)],  # more than sold
        [(0, 5), (0, 1)],  # the same row twice
        [(9, 1)],  # unknown row
        [(0, 5), (1, 5)],  # second row has only 4
    ],
)
def test_return_rejects_bad_selection_atomically(db, client, lines) -> None:
    order, _, _ = _sent_order()

    with pytest.raises(WarehouseItemBadRequestError):
        _return(client, order, *lines)

    assert order.items.count() == 2
    assert not InboundWarehouseOrder.objects.filter(return_order=order).exists()
    assert not CreditNoteToCustomer.objects.exists()


def test_return_exactly_the_sold_amount_is_allowed(db, client) -> None:
    order, first, _ = _sent_order()

    assert _return(client, order, (first.index, 10)).status_code == 200


def test_return_cannot_exceed_what_is_left_after_previous_returns(db, client) -> None:
    order, first, _ = _sent_order()
    assert _return(client, order, (first.index, 7)).status_code == 200

    with pytest.raises(WarehouseItemBadRequestError, match="only 3"):
        _return(client, order, (first.index, 4))

    assert _return(client, order, (first.index, 3)).status_code == 200


def test_return_of_a_returned_row_is_rejected(db, client) -> None:
    order, first, _ = _sent_order()
    _return(client, order, (first.index, 2))
    returned = order.items.get(is_returned=True)

    with pytest.raises(WarehouseItemBadRequestError):
        _return(client, order, (returned.index, 1))


def test_return_of_non_physical_product_is_rejected(db, client) -> None:
    order = OutboundOrderFactory.it(state=OutboundOrderState.SENT)
    service = StockProductFactory(type=ProductTypeFactory(non_physical=True))
    item = OutboundOrderItemFactory.it(order=order, stock_product=service, amount=1)

    with pytest.raises(WarehouseItemBadRequestError, match="not a physical"):
        _return(client, order, (item.index, 1))


def test_every_return_gets_its_own_receipt_and_credit_note(db, client) -> None:
    order, first, second = _sent_order()

    _return(client, order, (first.index, 1))
    res = _return(client, order, (second.index, 1))

    data = res.json()["data"]
    receipts = sorted(w["code"] for w in data["return_warehouse_orders"])
    assert len(receipts) == 2 and receipts[0].endswith("001")
    assert receipts[1].endswith("002")
    assert len({n["code"] for n in data["credit_notes"]}) == 2
    # each credit note holds only the rows of its own return
    assert sorted(len(n["items"]) for n in data["credit_notes"]) == [1, 1]
    assert [r["index"] for r in data["items"]] == [0, 1, 2, 3]


def test_returned_rows_are_not_picked(db, client) -> None:
    order, first, _ = _sent_order()
    _return(client, order, (first.index, 2))

    returned = order.items.get(is_returned=True)

    assert not OutboundWarehouseOrderItem.objects.filter(
        source_order_item=returned
    ).exists()
    assert not outbound_orders_service._has_physical_items(
        OutboundOrderFactory.it(state=OutboundOrderState.SENT)
    )


def test_bulk_origin_country_skips_returned_rows(db, client) -> None:
    order, first, _ = _sent_order()
    _return(client, order, (first.index, 2))

    outbound_orders_service.set_items_required_origin_country(
        order.code, "CZ", RequestContext(user_id=None)
    )

    assert order.items.get(is_returned=True).required_origin_country is None
    assert not OutboundWarehouseOrderItem.objects.filter(
        source_order_item__is_returned=True
    ).exists()


def test_total_weight_is_net_of_returned_goods(db, client) -> None:
    order, first, _ = _sent_order()
    first.stock_product.unit_weight = Decimal("2")
    first.stock_product.save()
    second_weight = Decimal("1") * 4  # factory default weight of 1 per unit

    res = _return(client, order, (first.index, 3))

    assert res.json()["data"]["total_weight"] == float(
        Decimal("2") * (10 - 3) + second_weight
    )


def test_returned_rows_are_read_only(db, client) -> None:
    order, first, _ = _sent_order()
    _return(client, order, (first.index, 2))
    returned = order.items.get(is_returned=True)

    with pytest.raises(WarehouseItemBadRequestError):
        client.delete(f"/{order.code}/items/{returned.index}")
    # the sold row cannot vanish from under its return either
    with pytest.raises(WarehouseItemBadRequestError):
        client.delete(f"/{order.code}/items/{first.index}")


def test_duplicate_leaves_returned_rows_out(db, client) -> None:
    order, first, _ = _sent_order()
    _return(client, order, (first.index, 2))

    res = client.post(f"/{order.code}/duplicate")

    copy = res.json()["data"]
    assert [i["is_returned"] for i in copy["items"]] == [False, False]
    assert copy["credit_notes"] == [] and copy["return_warehouse_orders"] == []


def test_receiving_returned_goods_end_to_end(db, client) -> None:
    order, first, _ = _sent_order()
    # the goods left the warehouse at cost of 12 per unit
    OutboundWarehouseOrderItemFactory(
        warehouse_order=WarehouseOrderOutFactory(order=order),
        source_order_item=first,
        amount=Decimal("10"),
        price_at_shipment=Decimal("120"),
    )
    _return(client, order, (first.index, 4))
    receipt = InboundWarehouseOrder.objects.get(return_order=order)
    location = WarehouseLocationFactory(is_putaway=True)
    warehouse = TestClient(warehouse_routes)

    # arrival: the receipt is prepared from the returned rows
    res = warehouse.post(
        f"/orders-incoming/{receipt.code}/transition",
        json={"location_code": location.code},
    )
    assert res.status_code == 200, res.content
    data = res.json()["data"]
    assert data["state"] == "draft"
    assert data["order"]["type"] == "Outbound" and data["order"]["code"] == order.code
    [line] = data["order_items"]
    assert line["product"]["code"] == first.stock_product.code
    assert Decimal(str(line["amount"])) == 4
    assert Decimal(str(line["unit_price_at_receipt"])) == 12
    assert data["credit_note"]["state"] == "draft"

    # confirmation: goods are in stock, the credit note is final
    res = warehouse.post(f"/orders-incoming/{receipt.code}/transition", json={})
    assert res.status_code == 200, res.content
    data = res.json()["data"]
    assert data["state"] == "pending"
    assert data["credit_note"]["state"] == "confirmed"
    assert sum(Decimal(str(i["amount"])) for i in data["items"]) == 4
    assert (
        CreditNoteToCustomer.objects.get(order=order).state == CreditNoteState.CONFIRMED
    )

    # the sales order itself carries the receipt and the confirmed note
    detail = client.get(f"/{order.code}").json()["data"]
    assert detail["return_warehouse_orders"][0]["state"] == "pending"
    assert detail["credit_notes"][0]["state"] == "confirmed"


def test_receipt_of_return_is_listed_and_searchable(db, client) -> None:
    order, first, _ = _sent_order()
    _return(client, order, (first.index, 1))
    receipt = InboundWarehouseOrder.objects.get(return_order=order)
    warehouse = TestClient(warehouse_routes)

    listed = warehouse.get("/orders-incoming", query_params={"search_term": order.code})

    assert listed.status_code == 200
    assert [w["code"] for w in listed.json()["data"]] == [receipt.code]


def test_customer_credit_note_detail(db, client) -> None:
    order, first, _ = _sent_order()
    _return(client, order, (first.index, 1))
    note = CreditNoteToCustomer.objects.get(order=order)

    res = TestClient(credit_note_routes).get(f"/{note.code}")

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["code"] == note.code
    assert data["order"]["code"] == order.code and data["order"]["type"] == "Outbound"
    assert len(data["items"]) == 1


def test_receipt_must_have_exactly_one_parent(db) -> None:
    from django.db import IntegrityError, transaction

    from apps.warehouse.tests.factories.order import InboundOrderFactory

    order = OutboundOrderFactory.it(state=OutboundOrderState.SENT)

    with pytest.raises(IntegrityError), transaction.atomic():
        InboundWarehouseOrder.objects.create(
            code="X1", order=InboundOrderFactory.it(), return_order=order
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        InboundWarehouseOrder.objects.create(code="X2")
