"""Product types flagged `non_physical` (services, fees...) are never picked."""

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.outbound_orders import routes as outbound_routes
from apps.warehouse.api.routes.product import routes as product_routes
from apps.warehouse.core.schemas.warehouse import WarehouseOrderCreateSchema
from apps.warehouse.core.services.invoices import InvoicesService as InvoiceService
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.orders import OutboundOrderState
from apps.warehouse.models.product import ProductType
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrderItem,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderItem,
    WarehouseItem,
)
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import (
    ProductTypeFactory,
    StockProductFactory,
)
from apps.warehouse.tests.factories.warehouse import WarehouseLocationFactory


@pytest.fixture
def product_client() -> TestClient:
    return TestClient(product_routes)


@pytest.fixture
def outbound_client() -> TestClient:
    return TestClient(outbound_routes)


def _service_product():
    return StockProductFactory.it(
        type=ProductTypeFactory(name="Service", non_physical=True)
    )


# --- product type API -------------------------------------------------------------


def test_product_type_defaults_to_physical(db) -> None:
    assert ProductType.objects.create(name="Goods").non_physical is False


@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"name": "T"}, False),
        ({"name": "T", "non_physical": False}, False),
        ({"name": "T", "non_physical": True}, True),
    ],
)
def test_create_type_non_physical(db, product_client, payload, expected) -> None:
    res = product_client.post("/types", json=payload)

    assert res.status_code == 200
    assert res.json()["data"]["non_physical"] is expected
    assert ProductType.objects.get(name="T").non_physical is expected


@pytest.mark.parametrize("before, after", [(False, True), (True, False), (True, True)])
def test_update_type_non_physical(db, product_client, before, after) -> None:
    ProductTypeFactory(name="Old", non_physical=before)

    res = product_client.put("/types/Old", json={"name": "New", "non_physical": after})

    assert res.status_code == 200
    assert res.json()["data"]["non_physical"] is after
    assert ProductType.objects.get(name="New").non_physical is after


def test_update_type_omitting_flag_resets_to_default(db, product_client) -> None:
    ProductTypeFactory(name="Old", non_physical=True)

    res = product_client.put("/types/Old", json={"name": "Old"})

    assert res.status_code == 200
    assert ProductType.objects.get(name="Old").non_physical is False


def test_list_types_exposes_flag(db, product_client) -> None:
    ProductTypeFactory(name="Service", non_physical=True)

    res = product_client.get("/types")

    assert res.status_code == 200
    assert res.json()["data"][0]["non_physical"] is True


@pytest.mark.parametrize("non_physical", [True, False])
def test_product_exposes_type_flag(db, product_client, non_physical) -> None:
    product = StockProductFactory.it(
        type=ProductTypeFactory(name="X", non_physical=non_physical)
    )

    res = product_client.get(f"/{product.code}")

    assert res.status_code == 200
    assert res.json()["data"]["non_physical"] is non_physical


# --- outbound: no warehouse order items -------------------------------------------


def test_transition_skips_non_physical_items(db, outbound_client) -> None:
    order = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)
    physical = StockProductFactory.it()
    service = _service_product()
    OutboundOrderItemFactory(order=order, stock_product=physical, amount=3, index=0)
    OutboundOrderItemFactory(order=order, stock_product=service, amount=1, index=1)

    res = outbound_client.post(f"/{order.code}/transition", json={"action": "next"})

    assert res.status_code == 200
    items = OutboundWarehouseOrderItem.objects.filter(warehouse_order__order=order)
    assert [i.stock_product for i in items] == [physical]
    assert order.items.count() == 2


def test_transition_with_only_non_physical_items_creates_no_warehouse_order(
    db, outbound_client
) -> None:
    order = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)
    OutboundOrderItemFactory(order=order, stock_product=_service_product(), amount=1)

    res = outbound_client.post(f"/{order.code}/transition", json={"action": "next"})

    assert res.status_code == 200
    order.refresh_from_db()
    assert order.state == OutboundOrderState.PICKING
    assert not OutboundWarehouseOrder.objects.filter(order=order).exists()
    # nothing to wait for -> may be invoiced right away
    assert InvoiceService._has_completed_warehouse_order(order) is True


def test_non_physical_only_order_without_items_is_not_invoiceable(db) -> None:
    order = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)

    assert InvoiceService._has_completed_warehouse_order(order) is False


def test_physical_order_still_waits_for_warehouse_order(db) -> None:
    order = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)
    OutboundOrderItemFactory(order=order, stock_product=StockProductFactory.it())

    assert InvoiceService._has_completed_warehouse_order(order) is False


@pytest.mark.parametrize("non_physical", [True, False])
def test_item_added_after_picking_started(db, outbound_client, non_physical) -> None:
    order = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)
    OutboundOrderItemFactory(order=order, stock_product=StockProductFactory.it())
    outbound_client.post(f"/{order.code}/transition", json={"action": "next"})
    product = _service_product() if non_physical else StockProductFactory.it()
    before = OutboundWarehouseOrderItem.objects.filter(
        warehouse_order__order=order
    ).count()

    res = outbound_client.post(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 2,
            "total_price": 20,
        },
    )

    assert res.status_code == 200
    after = OutboundWarehouseOrderItem.objects.filter(
        warehouse_order__order=order
    ).count()
    assert after == before + (0 if non_physical else 1)


# --- inbound: no warehouse items --------------------------------------------------


def test_confirm_arrival_skips_non_physical_items(db, context) -> None:
    putaway = WarehouseLocationFactory.it(is_putaway=True)
    order = InboundOrderFactory.it()
    physical = StockProductFactory.it()
    InboundOrderItemFactory.it(order=order, stock_product=physical)
    InboundOrderItemFactory.it(order=order, stock_product=_service_product())
    w_order = warehouse_service.create_inbound_order(
        WarehouseOrderCreateSchema(purchase_order_code=order.code), context=context
    )

    warehouse_service.confirm_arrival(w_order.code, putaway.code, context=context)

    rows = InboundWarehouseOrderItem.objects.filter(warehouse_order__code=w_order.code)
    assert [r.stock_product for r in rows] == [physical]
    assert not WarehouseItem.objects.filter(
        stock_product__type__non_physical=True
    ).exists()
