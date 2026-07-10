import pytest
from django.core.exceptions import ObjectDoesNotExist

from apps.warehouse.core.services.item_reorder import reorder_order_items
from apps.warehouse.models.orders import InboundOrderItem
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory


def _make_items(order, count: int) -> list[InboundOrderItem]:
    """Create `count` items with sequential indices 0..count-1."""
    return [
        InboundOrderItemFactory.it(
            order=order, index=i, stock_product=StockProductFactory.it()
        )
        for i in range(count)
    ]


def _indices(order) -> list[int]:
    return list(order.items.order_by("index").values_list("index", flat=True))


def test_reorder_moves_item_forward(db):
    order = InboundOrderFactory.it()
    _make_items(order, 5)  # indices 0,1,2,3,4

    reorder_order_items(order.items, item_index=1, new_index=3)

    # item that was at 1 is now at 3; others shift left
    assert _indices(order) == [0, 1, 2, 3, 4]
    items = list(order.items.order_by("index"))
    # original positions: A=0,B=1,C=2,D=3,E=4  ->  A=0,C=1,D=2,B=3,E=4
    assert items[3].index == 3


def test_reorder_moves_item_backward(db):
    order = InboundOrderFactory.it()
    _make_items(order, 4)  # indices 0,1,2,3

    item_at_3 = order.items.get(index=3)
    reorder_order_items(order.items, item_index=3, new_index=1)

    item_at_3.refresh_from_db()
    assert item_at_3.index == 1
    assert _indices(order) == [0, 1, 2, 3]


def test_reorder_to_same_position_is_noop(db):
    order = InboundOrderFactory.it()
    _make_items(order, 3)

    before = _indices(order)
    reorder_order_items(order.items, item_index=1, new_index=1)
    assert _indices(order) == before


def test_reorder_clamps_new_index_above_last(db):
    order = InboundOrderFactory.it()
    _make_items(order, 3)  # indices 0,1,2

    item_at_0 = order.items.get(index=0)
    reorder_order_items(order.items, item_index=0, new_index=999)

    item_at_0.refresh_from_db()
    assert item_at_0.index == 2  # clamped to last position
    assert _indices(order) == [0, 1, 2]


def test_reorder_clamps_new_index_below_zero(db):
    order = InboundOrderFactory.it()
    _make_items(order, 3)

    item_at_2 = order.items.get(index=2)
    reorder_order_items(order.items, item_index=2, new_index=-5)

    item_at_2.refresh_from_db()
    assert item_at_2.index == 0
    assert _indices(order) == [0, 1, 2]


def test_reorder_indices_always_sequential(db):
    order = InboundOrderFactory.it()
    # Create items with non-sequential indices (simulating legacy data)
    for i, sparse_index in enumerate([0, 5, 10, 15]):
        InboundOrderItemFactory.it(
            order=order, index=sparse_index, stock_product=StockProductFactory.it()
        )

    reorder_order_items(order.items, item_index=5, new_index=2)

    assert _indices(order) == [0, 1, 2, 3]


def test_reorder_raises_for_missing_item_index(db):
    order = InboundOrderFactory.it()
    _make_items(order, 3)

    with pytest.raises(ObjectDoesNotExist):
        reorder_order_items(order.items, item_index=99, new_index=0)


def test_reorder_single_item_is_noop(db):
    order = InboundOrderFactory.it()
    InboundOrderItemFactory.it(
        order=order, index=0, stock_product=StockProductFactory.it()
    )

    reorder_order_items(order.items, item_index=0, new_index=0)
    assert _indices(order) == [0]


def test_reorder_api_endpoint_inbound(db):
    from ninja.testing import TestClient
    from apps.warehouse.api.routes.inbound_orders import routes

    order = InboundOrderFactory.it()
    _make_items(order, 4)

    client = TestClient(routes)
    res = client.put(
        f"/{order.code}/items/0/reorder",
        json={"new_index": 3},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["code"] == order.code
    assert [item["index"] for item in body["data"]["items"]] == [0, 1, 2, 3]
    assert _indices(order) == [0, 1, 2, 3]

    item_moved = order.items.order_by("index").last()
    assert item_moved is not None


def test_reorder_api_endpoint_outbound(db):
    from ninja.testing import TestClient
    from apps.warehouse.api.routes.outbound_orders import routes
    from apps.warehouse.tests.factories.order import (
        OutboundOrderFactory,
        OutboundOrderItemFactory,
    )

    order = OutboundOrderFactory.it()
    for i in range(4):
        OutboundOrderItemFactory.it(
            order=order, index=i, stock_product=StockProductFactory.it()
        )

    client = TestClient(routes)
    res = client.put(
        f"/{order.code}/items/3/reorder",
        json={"new_index": 0},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["code"] == order.code
    assert [item["index"] for item in body["data"]["items"]] == [0, 1, 2, 3]
