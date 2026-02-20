from decimal import Decimal

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.inbound_orders import routes as order_routes
from apps.warehouse.api.routes.warehouse import routes as warehouse_routes
from apps.warehouse.core.schemas.orders import InboundOrderCreateOrUpdateSchema
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrderState,
    InboundWarehouseOrder,
)
from apps.warehouse.models.orders import (
    CreditNoteState,
    InboundOrderState,
    InboundOrder,
)

from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.warehouse import WarehouseLocationFactory
from apps.warehouse.tests.factories.order import StockProductFactory


@pytest.fixture
def order_client() -> TestClient:
    return TestClient(order_routes)


@pytest.fixture
def warehouse_client() -> TestClient:
    return TestClient(warehouse_routes)


def test_inbound_order_end_2_end(db, order_client, warehouse_client):
    # 1. Setup
    supplier = CustomerFactory()
    product_1 = StockProductFactory()
    product_2 = StockProductFactory()
    receiving_location = WarehouseLocationFactory(is_putaway=True)
    storage_location_1 = WarehouseLocationFactory(is_putaway=False)
    storage_location_2 = WarehouseLocationFactory(is_putaway=False)

    # 2. Create Inbound Order
    payload = InboundOrderCreateOrUpdateSchema(
        supplier_code=supplier.code,
        supplier_name=supplier.name,
        external_code="EXT-123",
        currency="CZK",
    )
    res = order_client.post("/", json=payload.model_dump())
    assert res.status_code == 200
    order_code = res.json()["data"]["code"]

    order_db = InboundOrder.objects.get(code=order_code)

    # Add items to the order
    item_1_data = {
        "product_code": product_1.code,
        "product_name": product_1.name,
        "amount": 100,
        "unit_price": 10.5,
    }
    res = order_client.post(f"/{order_code}/items", json=item_1_data)
    assert res.status_code == 200

    order_db.refresh_from_db()
    assert order_db.items.count() == 1

    item_2_data = {
        "product_code": product_2.code,
        "product_name": product_2.name,
        "amount": 50,
        "unit_price": 25.0,
    }
    res = order_client.post(f"/{order_code}/items", json=item_2_data)
    assert res.status_code == 200

    order_db.refresh_from_db()
    assert order_db.items.count() == 2
    assert order_db.state == InboundOrderState.DRAFT

    res = order_client.get(f"/{order_code}")
    assert res.json()["data"]["state"] == InboundOrderState.DRAFT

    # 3. Submit Order
    res = order_client.patch(f"/{order_code}/state", json={"state": "submitted"})
    assert res.status_code == 200
    assert res.json()["data"]["state"] == InboundOrderState.SUBMITTED

    order_db.refresh_from_db()
    assert order_db.state == InboundOrderState.SUBMITTED

    # 4. Create Inbound Warehouse Order (Receiving)
    res = warehouse_client.post(
        "/orders-incoming",
        json={
            "purchase_order_code": order_code,
            "location_code": receiving_location.code,
        },
    )
    assert res.status_code == 200
    w_order_res = res.json()["data"]
    w_order_code = w_order_res["code"]
    assert w_order_res["state"] == InboundWarehouseOrderState.DRAFT
    assert w_order_res["order"]["state"] == InboundOrderState.RECEIVING
    assert len(w_order_res["items"]) == 2

    order_db.refresh_from_db()
    w_order_db = InboundWarehouseOrder.objects.get(code=w_order_code)
    assert w_order_db.state == InboundWarehouseOrderState.DRAFT
    assert order_db.state == InboundOrderState.RECEIVING
    assert order_db.warehouse_order.code == w_order_code

    # 5. Create Credit Note
    item_to_return = next(
        item
        for item in w_order_res["items"]
        if item["product"]["code"] == product_1.code
    )
    return_amount = 20
    res = warehouse_client.post(
        f"/orders-incoming/{w_order_code}/credit",
        json={"item_id": item_to_return["id"], "amount": return_amount},
    )
    assert res.status_code == 200
    w_order_res = res.json()["data"]
    assert w_order_res["credit_note"] is not None
    assert w_order_res["credit_note"]["state"] == CreditNoteState.DRAFT
    updated_item = next(
        item
        for item in w_order_res["items"]
        if item["product"]["code"] == product_1.code
    )
    assert Decimal(str(updated_item["amount"])) == Decimal(
        str(item_to_return["amount"])
    ) - Decimal(return_amount)

    # 6. Confirm Warehouse Order
    res = warehouse_client.post(
        f"/orders-incoming/{w_order_code}/state", json={"state": "pending"}
    )
    assert res.status_code == 200
    w_order_res = res.json()["data"]
    assert w_order_res["state"] == InboundWarehouseOrderState.PENDING
    assert w_order_res["order"]["state"] == InboundOrderState.PUTAWAY
    assert w_order_res["credit_note"]["state"] == CreditNoteState.CONFIRMED

    # 7. Putaway Items
    items_to_putaway = w_order_res["items"]
    for i, item in enumerate(items_to_putaway):
        new_location = (
            storage_location_1
            if item["product"]["code"] == product_1.code
            else storage_location_2
        )
        res = warehouse_client.post(
            f"/orders-incoming/{w_order_code}/items/{item['id']}/putaway",
            json={"new_location_code": new_location.code},
        )
        assert res.status_code == 200
        w_order_res = res.json()["data"]

        # Verify state transitions during putaway
        if i < len(items_to_putaway) - 1:
            assert w_order_res["state"] == InboundWarehouseOrderState.STARTED
        else:
            # After last item is put away, orders should be completed
            assert w_order_res["state"] == InboundWarehouseOrderState.COMPLETED
            assert w_order_res["order"]["state"] == InboundOrderState.COMPLETED

    # 8. Final Verification
    res = warehouse_client.get(f"/locations/{storage_location_1.code}")
    assert res.status_code == 200
    location_1_items = res.json()["data"]["items"]
    assert len(location_1_items) == 1
    assert location_1_items[0]["product"]["code"] == product_1.code
    assert (
        Decimal(str(location_1_items[0]["amount"]))
        == Decimal(str(item_to_return["amount"])) - return_amount
    )

    res = warehouse_client.get(f"/locations/{storage_location_2.code}")
    assert res.status_code == 200
    location_2_items = res.json()["data"]["items"]
    assert len(location_2_items) == 1
    assert location_2_items[0]["product"]["code"] == product_2.code

    order_db.refresh_from_db()
    w_order_db.refresh_from_db()
    assert order_db.state == InboundOrderState.COMPLETED
    assert w_order_db.state == InboundWarehouseOrderState.COMPLETED

    receiving_location.refresh_from_db()
    assert receiving_location.items.count() == 0
