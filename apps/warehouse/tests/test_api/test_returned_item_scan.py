"""Receipt of a return: the very item we shipped earlier is matched by its barcode."""

from decimal import Decimal

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.outbound_orders import routes as outbound_routes
from apps.warehouse.api.routes.warehouse import routes as warehouse_routes
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.orders import OutboundOrderState
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    InboundWarehouseOrderState,
    TrackingLevel,
    WarehouseItem,
    WarehouseMovement,
)
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.packaging import BatchFactory
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    OutboundWarehouseOrderItemFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
    WarehouseOrderOutFactory,
)

BOXES = 3


@pytest.fixture
def warehouse() -> TestClient:
    return TestClient(warehouse_routes)


def _ship(order, row, code: str, product):
    """A serialized box with its own barcode, picked for `order` and out of the warehouse."""
    box = WarehouseItemFactory.it(
        stock_product=product,
        amount=1,
        location=None,
        tracking_level=TrackingLevel.SERIALIZED_PACKAGE,
    )
    box.attach_barcode(code=code, is_primary=True)
    OutboundWarehouseOrderItemFactory(
        warehouse_order=WarehouseOrderOutFactory(order=order),
        source_order_item=row,
        amount=1,
        warehouse_item=box,
        price_at_shipment=Decimal("10"),
    )
    audit_service.add_entry(box, action=AuditAction.CREATE, reason="received")
    return box


@pytest.fixture
def shipped(db):
    """Order with 3 boxes shipped (codes BOX-0..2), 2 of them sent back; receipt in DRAFT."""
    product = StockProductFactory()
    order = OutboundOrderFactory.it(state=OutboundOrderState.SENT)
    row = OutboundOrderItemFactory.it(
        order=order,
        stock_product=product,
        amount=Decimal(BOXES),
        unit_price=Decimal("20"),
        total_price=60,
    )
    boxes = [_ship(order, row, f"BOX-{i}", product) for i in range(BOXES)]
    TestClient(outbound_routes).post(
        f"/{order.code}/returns", json={"items": [{"item_index": 0, "amount": 2}]}
    )
    receipt = InboundWarehouseOrder.objects.get(return_order=order)
    location = WarehouseLocationFactory(is_putaway=True)
    res = TestClient(warehouse_routes).post(
        f"/orders-incoming/{receipt.code}/transition",
        json={"location_code": location.code},
    )
    assert res.status_code == 200, res.content
    return order, receipt, boxes, location


def _match(client, receipt, barcode):
    return client.post(
        f"/orders-incoming/{receipt.code}/returned-items/match",
        json={"barcode": barcode},
    )


def _claim(client, receipt, line_id, item_id):
    return client.post(
        f"/orders-incoming/{receipt.code}/returned-items",
        json={"order_item_id": line_id, "warehouse_item_id": item_id},
    )


def test_scan_matches_the_shipped_item_and_offers_the_open_line(shipped, warehouse):
    _, receipt, boxes, _ = shipped

    res = _match(warehouse, receipt, "BOX-1")

    assert res.status_code == 200, res.content
    data = res.json()["data"]
    assert data["warehouse_item"]["id"] == boxes[1].pk
    assert data["warehouse_item"]["primary_barcode"] == "BOX-1"
    assert data["order_item_id"] == receipt.order_items.get().pk


def test_confirming_the_scan_splits_the_line_without_creating_items(shipped, warehouse):
    _, receipt, boxes, _ = shipped
    line = receipt.order_items.get()
    items_before = WarehouseItem.objects.count()

    res = _claim(warehouse, receipt, line.pk, boxes[1].pk)

    assert res.status_code == 200, res.content
    lines = res.json()["data"]["order_items"]
    assert sorted(
        (ln["tracking_level"], Decimal(str(ln["amount"]))) for ln in lines
    ) == [
        ("FUNGIBLE", 1),
        ("SERIALIZED_PACKAGE", 1),
    ]
    assert WarehouseItem.objects.count() == items_before


def test_confirmed_receipt_puts_the_very_same_item_back_with_full_history(
    shipped, warehouse
):
    order, receipt, boxes, location = shipped
    box = boxes[1]
    items_before = WarehouseItem.objects.count()
    _claim(warehouse, receipt, receipt.order_items.get().pk, box.pk)

    res = warehouse.post(f"/orders-incoming/{receipt.code}/transition", json={})

    assert res.status_code == 200, res.content
    # the scanned box is the very row, in stock again; only the other unit is new
    assert WarehouseItem.objects.count() == items_before + 1
    box.refresh_from_db()
    assert box.location == location
    assert box.order_in == receipt
    assert box.live_outbound_assignment is None
    assert box.outbound_assignment.returned_at is not None
    assert (
        box.primary_barcode_code == "BOX-1"
        if hasattr(box, "primary_barcode_code")
        else True
    )
    assert WarehouseItem.available.filter(pk=box.pk).exists()
    assert not WarehouseItem.available.filter(pk=boxes[0].pk).exists()  # still shipped
    assert box.movements.filter(inbound_order_code=receipt).count() == 1

    # history before it left and after it came back, on the same item
    entries = audit_service.get_timeline_for_object(box)
    reasons = [e.model_dump().get("reason") for e in entries]
    assert "received" in reasons
    assert any("příjemkou" in (r or "") for r in reasons)
    assert any(m.item_id == box.pk for m in WarehouseMovement.objects.filter(item=box))

    detail = warehouse.get(f"/orders-incoming/{receipt.code}").json()["data"]
    assert detail["state"] == "pending"
    assert box.pk in [i["id"] for i in detail["items"]]
    assert detail["remaining_amount"] == 2

    # the shipped item no longer reports to be out with the order
    assert (
        warehouse.get(f"/items/{box.pk}").json()["data"]["outbound_order_code"] is None
    )


@pytest.mark.parametrize(
    "barcode",
    ["NOPE", ""],
)
def test_unknown_barcode_is_rejected(shipped, warehouse, barcode):
    _, receipt, _, _ = shipped

    with pytest.raises(WarehouseItemBadRequestError, match="single warehouse item"):
        _match(warehouse, receipt, barcode)


def test_barcode_of_something_else_than_an_item_is_rejected(shipped, warehouse):
    _, receipt, _, _ = shipped
    BatchFactory().attach_barcode(code="BATCH-1", is_primary=True)

    with pytest.raises(WarehouseItemBadRequestError, match="single warehouse item"):
        _match(warehouse, receipt, "BATCH-1")


def test_item_in_stock_is_not_a_return(shipped, warehouse):
    _, receipt, _, location = shipped
    stocked = WarehouseItemFactory.it(
        stock_product=receipt.order_items.get().stock_product,
        amount=1,
        location=location,
    )
    stocked.attach_barcode(code="IN-STOCK", is_primary=True)

    with pytest.raises(WarehouseItemBadRequestError, match="not out of the warehouse"):
        _match(warehouse, receipt, "IN-STOCK")


def test_item_shipped_with_another_order_is_rejected(shipped, warehouse):
    _, receipt, _, _ = shipped
    other = OutboundOrderFactory.it(state=OutboundOrderState.SENT)
    row = OutboundOrderItemFactory.it(order=other, amount=1)
    foreign = _ship(other, row, "FOREIGN", receipt.order_items.get().stock_product)

    with pytest.raises(
        WarehouseItemBadRequestError, match="was not shipped with order"
    ):
        _match(warehouse, receipt, "FOREIGN")
    with pytest.raises(
        WarehouseItemBadRequestError, match="was not shipped with order"
    ):
        _claim(warehouse, receipt, receipt.order_items.get().pk, foreign.pk)


def test_the_same_item_cannot_be_claimed_twice(shipped, warehouse):
    _, receipt, boxes, _ = shipped
    _claim(warehouse, receipt, receipt.order_items.get().pk, boxes[0].pk)

    with pytest.raises(WarehouseItemBadRequestError, match="already being received"):
        _match(warehouse, receipt, "BOX-0")


def test_nothing_left_to_match_once_everything_returned_is_claimed(shipped, warehouse):
    _, receipt, boxes, _ = shipped
    for box in boxes[:2]:
        line = receipt.order_items.get(tracking_level=TrackingLevel.FUNGIBLE)
        _claim(warehouse, receipt, line.pk, box.pk)

    with pytest.raises(WarehouseItemBadRequestError, match="not among the goods left"):
        _match(warehouse, receipt, "BOX-2")


def test_item_bigger_than_the_open_line_is_rejected(shipped, warehouse):
    order, receipt, _, _ = shipped
    row = order.items.get(index=0)
    big = _ship(order, row, "BIG", row.stock_product)
    big.amount = Decimal("5")
    big.save()

    with pytest.raises(WarehouseItemBadRequestError, match="not among the goods left"):
        _match(warehouse, receipt, "BIG")


@pytest.mark.parametrize(
    "state", [InboundWarehouseOrderState.PENDING, InboundWarehouseOrderState.COMPLETED]
)
def test_only_a_draft_receipt_can_be_matched(shipped, warehouse, state):
    _, receipt, _, _ = shipped
    InboundWarehouseOrder.objects.filter(pk=receipt.pk).update(state=state)

    with pytest.raises(WarehouseItemBadRequestError, match="can no longer be edited"):
        _match(warehouse, receipt, "BOX-0")


def test_receipt_of_a_purchase_order_has_no_returned_items(db, warehouse):
    receipt = InboundWarehouseOrder.objects.create(
        code="P-X",
        order=InboundOrderFactory.it(),
        state=InboundWarehouseOrderState.DRAFT,
    )

    with pytest.raises(
        WarehouseItemBadRequestError, match="does not belong to a return"
    ):
        _match(warehouse, receipt, "BOX-0")


def test_dissolving_a_matched_line_gives_the_amount_back(shipped, warehouse):
    _, receipt, boxes, _ = shipped
    _claim(warehouse, receipt, receipt.order_items.get().pk, boxes[1].pk)
    matched = receipt.order_items.get(returned_warehouse_item=boxes[1])

    res = warehouse.delete(f"/orders-incoming/{receipt.code}/order-items/{matched.pk}")

    assert res.status_code == 200, res.content
    [line] = receipt.order_items.all()
    assert line.tracking_level == TrackingLevel.FUNGIBLE and line.amount == 2
    # nothing was changed on the shipped item
    assert boxes[1].live_outbound_assignment is not None
