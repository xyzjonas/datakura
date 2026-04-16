"""Tests for the offload-to-child-order feature."""

from decimal import Decimal

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.warehouse import routes
from apps.warehouse.core.exceptions import WarehouseGenericError
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    InboundWarehouseOrderItem,
    InboundWarehouseOrderState,
)
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    InboundWarehouseOrderItemFactory,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


# ---------------------------------------------------------------------------
# create_child_warehouse_order
# ---------------------------------------------------------------------------


def test_create_child_order_creates_new_order(db, context) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)

    child = warehouse_service.create_child_warehouse_order(parent.code, context)

    assert child.pk is not None
    assert child.primary_order == parent
    assert child.order == parent.order
    assert child.state == InboundWarehouseOrderState.DRAFT


def test_create_child_order_links_same_inbound_order(db, context) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)

    child = warehouse_service.create_child_warehouse_order(parent.code, context)

    assert child.order_id == parent.order_id


def test_create_child_order_generates_unique_code(db, context) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)

    child = warehouse_service.create_child_warehouse_order(parent.code, context)

    assert child.code != parent.code
    assert InboundWarehouseOrder.objects.filter(code=child.code).exists()


def test_create_child_order_inherits_pickup_location(db, context) -> None:
    from apps.warehouse.tests.factories.warehouse import WarehouseLocationFactory

    pickup = WarehouseLocationFactory()
    parent = InboundWarehouseOrderFactory.it(
        state=InboundWarehouseOrderState.DRAFT, pickup_location=pickup
    )

    child = warehouse_service.create_child_warehouse_order(parent.code, context)

    assert child.pickup_location == pickup


# ---------------------------------------------------------------------------
# offload_items_to_child_order (DRAFT mode — operates on InboundWarehouseOrderItem)
# ---------------------------------------------------------------------------


def test_offload_full_item_moves_to_child(db, context) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)
    item = InboundWarehouseOrderItemFactory.it(
        warehouse_order=parent, amount=Decimal("10")
    )

    warehouse_service.offload_items_to_child_order(
        parent_code=parent.code,
        items=[(item.pk, Decimal("10"))],
        context=context,
    )

    item.refresh_from_db()
    assert item.warehouse_order != parent
    child = item.warehouse_order
    assert child is not None
    assert child.primary_order == parent


def test_offload_partial_amount_splits_item(db, context) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)
    item = InboundWarehouseOrderItemFactory.it(
        warehouse_order=parent, amount=Decimal("10")
    )

    warehouse_service.offload_items_to_child_order(
        parent_code=parent.code,
        items=[(item.pk, Decimal("3"))],
        context=context,
    )

    item.refresh_from_db()
    assert item.amount == Decimal("7")
    assert item.warehouse_order == parent

    child_item = InboundWarehouseOrderItem.objects.get(
        stock_product=item.stock_product,
        amount=Decimal("3"),
        warehouse_order__primary_order=parent,
    )
    assert child_item.warehouse_order.primary_order == parent


def test_offload_reuses_existing_draft_child(db, context) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)
    child = InboundWarehouseOrderFactory.it(
        order=parent.order,
        primary_order=parent,
        state=InboundWarehouseOrderState.DRAFT,
    )
    item = InboundWarehouseOrderItemFactory.it(
        warehouse_order=parent, amount=Decimal("5")
    )

    warehouse_service.offload_items_to_child_order(
        parent_code=parent.code,
        items=[(item.pk, Decimal("5"))],
        context=context,
    )

    item.refresh_from_db()
    assert item.warehouse_order == child
    # No new child order was created
    assert parent.derived_orders.count() == 1


def test_offload_exceeds_amount_raises(db, context) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)
    item = InboundWarehouseOrderItemFactory.it(
        warehouse_order=parent, amount=Decimal("5")
    )

    with pytest.raises(WarehouseGenericError):
        warehouse_service.offload_items_to_child_order(
            parent_code=parent.code,
            items=[(item.pk, Decimal("99"))],
            context=context,
        )


def test_offload_multiple_items(db, context) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)
    item1 = InboundWarehouseOrderItemFactory.it(
        warehouse_order=parent, amount=Decimal("4")
    )
    item2 = InboundWarehouseOrderItemFactory.it(
        warehouse_order=parent, amount=Decimal("8")
    )

    warehouse_service.offload_items_to_child_order(
        parent_code=parent.code,
        items=[(item1.pk, Decimal("4")), (item2.pk, Decimal("2"))],
        context=context,
    )

    item1.refresh_from_db()
    item2.refresh_from_db()
    # item1 fully offloaded to child
    assert item1.warehouse_order != parent
    child = item1.warehouse_order
    # item2 partially offloaded – original row still in parent
    assert item2.warehouse_order == parent
    assert item2.amount == Decimal("6")
    # The split piece went to the same child
    offloaded2 = InboundWarehouseOrderItem.objects.get(
        stock_product=item2.stock_product,
        warehouse_order=child,
    )
    assert offloaded2.amount == Decimal("2")


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------


def test_api_offload_returns_updated_parent_order(db, client) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)
    item = InboundWarehouseOrderItemFactory.it(
        warehouse_order=parent, amount=Decimal("10")
    )

    res = client.post(
        f"orders-incoming/{parent.code}/offload",
        json={"items": [{"item_id": item.pk, "amount": 10}]},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["data"]["code"] == parent.code


def test_api_offload_partial(db, client) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)
    item = InboundWarehouseOrderItemFactory.it(
        warehouse_order=parent, amount=Decimal("20")
    )

    res = client.post(
        f"orders-incoming/{parent.code}/offload",
        json={"items": [{"item_id": item.pk, "amount": 5}]},
    )

    assert res.status_code == 200
    item.refresh_from_db()
    assert item.amount == Decimal("15")


def test_api_offload_bad_amount_returns_error(db, client) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)
    item = InboundWarehouseOrderItemFactory.it(
        warehouse_order=parent, amount=Decimal("5")
    )

    with pytest.raises(WarehouseGenericError):
        client.post(
            f"orders-incoming/{parent.code}/offload",
            json={"items": [{"item_id": item.pk, "amount": 999}]},
        )


# ---------------------------------------------------------------------------
# Schema: parent/child codes visible in responses
# ---------------------------------------------------------------------------


def test_warehouse_order_schema_includes_child_codes(db, context) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)
    child = warehouse_service.create_child_warehouse_order(parent.code, context)

    schema = warehouse_service.get_inbound_warehouse_order(parent.code)

    assert child.code in [o.code for o in schema.child_orders]
    assert schema.parent_order is None


def test_warehouse_order_schema_includes_parent_code(db, context) -> None:
    parent = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.DRAFT)
    child = warehouse_service.create_child_warehouse_order(parent.code, context)

    child_schema = warehouse_service.get_inbound_warehouse_order(child.code)

    assert child_schema.parent_order
    assert child_schema.parent_order.code == parent.code
