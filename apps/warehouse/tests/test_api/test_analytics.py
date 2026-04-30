from decimal import Decimal
from typing import cast

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.analytics import routes
from apps.warehouse.core.services.inventory_snapshots import inventory_snapshot_service
from apps.warehouse.models.orders import InboundOrder
from apps.warehouse.models.warehouse import InboundWarehouseOrderState
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    InboundWarehouseOrderItemFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def create_snapshot_item(
    *,
    product_code: str,
    location_code: str,
    quantity: str,
    purchase_price: str,
    purchase_currency: str = "CZK",
    receipt_price: str | None = None,
    receipt_currency: str = "CZK",
):
    product = StockProductFactory(
        code=product_code,
        purchase_price=Decimal(purchase_price),
        currency=purchase_currency,
    )
    location = WarehouseLocationFactory(code=location_code)
    inbound_order = InboundWarehouseOrderFactory(
        state=InboundWarehouseOrderState.PENDING,
    )
    inbound_order_order = cast(InboundOrder, inbound_order.order)
    inbound_order_order.currency = receipt_currency
    inbound_order_order.save(update_fields=["currency"])

    source_order_item = None
    if receipt_price is not None:
        source_order_item = InboundWarehouseOrderItemFactory(
            warehouse_order=inbound_order,
            stock_product=product,
            amount=Decimal(quantity),
            unit_price_at_receipt=Decimal(receipt_price),
        )

    return WarehouseItemFactory(
        stock_product=product,
        amount=Decimal(quantity),
        location=location,
        order_in=inbound_order,
        source_order_item=source_order_item,
    )


def test_create_inventory_snapshot_api_returns_dual_valuation_rows(db, client):
    create_snapshot_item(
        product_code="API-001",
        location_code="A-11",
        quantity="2",
        purchase_price="12.00",
        receipt_price="9.50",
    )
    create_snapshot_item(
        product_code="API-002",
        location_code="A-12",
        quantity="3",
        purchase_price="5.00",
        receipt_price=None,
    )

    response = client.post("inventory-snapshots", json={})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["line_count"] == 2
    assert payload["receipt_unpriced_line_count"] == 1
    assert payload["receipt_complete"] is False
    assert payload["purchase_totals"] == [{"currency": "CZK", "value": "39.0000"}]
    assert payload["receipt_totals"] == [{"currency": "CZK", "value": "19.0000"}]
    assert payload["lines"][0]["product_code"] == "API-001"
    assert payload["lines"][1]["receipt_price_available"] is False
    assert (
        payload["lines"][1]["receipt_price_fallback_reason"]
        == "missing_source_order_item"
    )


def test_get_inventory_snapshots_api_lists_latest_first(db, client):
    create_snapshot_item(
        product_code="LIST-001",
        location_code="B-11",
        quantity="1",
        purchase_price="1.00",
        receipt_price="1.00",
    )

    first = inventory_snapshot_service.create_snapshot()
    second = inventory_snapshot_service.create_snapshot()

    response = client.get("inventory-snapshots")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert [row["id"] for row in payload["data"]] == [second.id, first.id]


def test_get_inventory_snapshot_detail_api_returns_lines(db, client):
    create_snapshot_item(
        product_code="DETAIL-001",
        location_code="C-11",
        quantity="4",
        purchase_price="3.25",
        receipt_price="2.75",
        receipt_currency="EUR",
    )
    snapshot = inventory_snapshot_service.create_snapshot()

    response = client.get(f"inventory-snapshots/{snapshot.id}")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == snapshot.id
    assert len(payload["lines"]) == 1
    assert payload["lines"][0]["receipt_currency"] == "EUR"


def test_get_inventory_value_api_returns_latest_snapshot_summary(db, client):
    create_snapshot_item(
        product_code="LATEST-001",
        location_code="D-11",
        quantity="2",
        purchase_price="7.00",
        receipt_price="6.00",
    )
    snapshot = inventory_snapshot_service.create_snapshot()

    response = client.get("inventory-value")

    assert response.status_code == 200
    payload = response.json()["data"]["snapshot"]
    assert payload["id"] == snapshot.id
    assert payload["purchase_totals"] == [{"currency": "CZK", "value": "14.0000"}]
