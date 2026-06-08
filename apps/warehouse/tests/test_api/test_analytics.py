from datetime import timedelta
from decimal import Decimal
from typing import cast

import pytest
from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.analytics import routes
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.inventory_snapshots import inventory_snapshot_service
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.models.orders import InboundOrder
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrderState,
    WarehouseMovement,
)
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    InboundWarehouseOrderItemFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
    WarehouseMovementFactory,
)
from apps.warehouse.tests.factories.user import UserFactory


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


def test_get_recent_activity_api_returns_latest_fifteen_entries(db, client):
    product = StockProductFactory(code="ACTIVITY-001")
    now = timezone.now()

    newest_log = None
    for index in range(16):
        log = audit_service.add_entry(
            product,
            action=AuditAction.UPDATE,
            reason=f"Aktivita {index}",
        )
        AuditLog.objects.filter(pk=log.pk).update(
            created=now - timedelta(minutes=index)
        )  # type: ignore
        if index == 0:
            newest_log = log

    response = client.get("recent-activity")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert len(payload) == 8
    assert payload[0]["message"] == "Aktivita 0"
    assert payload[-1]["message"] == "Aktivita 7"
    assert payload[0]["id"] == newest_log.pk


def test_get_recent_activity_api_uses_fallback_message_when_reason_missing(db, client):
    product = StockProductFactory(code="ACTIVITY-002", name="Fallback produkt")
    log = audit_service.add_entry(
        product,
        action=AuditAction.CREATE,
        reason=None,
        object_repr="Fallback produkt",
    )
    AuditLog.objects.filter(pk=log.pk).update(created=timezone.now())  # type: ignore

    response = client.get("recent-activity")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload[0]["message"] == "Vytvořen záznam: Fallback produkt"
    assert payload[0]["object_repr"] == "Fallback produkt"


def test_get_warehouse_movements_api_returns_paginated_results(db, client):
    product = StockProductFactory(code="MOVE-001", name="Test Product")
    location_from = WarehouseLocationFactory(code="A-01")
    location_to = WarehouseLocationFactory(code="B-02")
    worker = UserFactory(username="testworker")

    # Create 25 movements
    for i in range(25):
        WarehouseMovementFactory(
            stock_product=product,
            location_from=location_from,
            location_to=location_to,
            worker=worker,
            amount=Decimal(i + 1),
        )

    response = client.get("warehouse-movements?page=1&page_size=20")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 25
    assert len(payload["data"]) == 20
    assert payload["next"] == 2
    assert payload["previous"] is None

    response_page2 = client.get("warehouse-movements?page=2&page_size=20")
    payload_page2 = response_page2.json()
    assert len(payload_page2["data"]) == 5
    assert payload_page2["next"] is None
    assert payload_page2["previous"] == 1


def test_get_warehouse_movements_api_filters_by_date_range(db, client):
    product = StockProductFactory(code="MOVE-002")
    location = WarehouseLocationFactory()
    now = timezone.now()

    # Movement yesterday
    movement_old = WarehouseMovementFactory(stock_product=product, location_to=location)
    WarehouseMovement.objects.filter(pk=movement_old.pk).update(
        moved_at=now - timedelta(days=1)
    )

    # Movement today
    movement_today = WarehouseMovementFactory(
        stock_product=product, location_to=location
    )
    WarehouseMovement.objects.filter(pk=movement_today.pk).update(moved_at=now)

    # Movement tomorrow (future)
    movement_future = WarehouseMovementFactory(
        stock_product=product, location_to=location
    )
    WarehouseMovement.objects.filter(pk=movement_future.pk).update(
        moved_at=now + timedelta(days=1)
    )

    # Filter from today onwards
    from urllib.parse import quote

    from_date = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    response = client.get(f"warehouse-movements?from_date={quote(from_date)}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert payload["data"][0]["id"] in [movement_today.pk, movement_future.pk]

    # Filter up to today
    to_date = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
    response = client.get(f"warehouse-movements?to_date={quote(to_date)}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert movement_old.pk in [m["id"] for m in payload["data"]]


def test_get_warehouse_movements_api_filters_by_stock_product(db, client):
    product1 = StockProductFactory(code="PROD-001")
    product2 = StockProductFactory(code="PROD-002")
    location = WarehouseLocationFactory()

    movement1 = WarehouseMovementFactory(stock_product=product1, location_to=location)
    WarehouseMovementFactory(stock_product=product2, location_to=location)

    response = client.get(f"warehouse-movements?stock_product_id={product1.pk}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["data"][0]["id"] == movement1.pk
    assert payload["data"][0]["stock_product_code"] == "PROD-001"


def test_get_warehouse_movements_api_filters_by_locations(db, client):
    product = StockProductFactory()
    location_a = WarehouseLocationFactory(code="A-01")
    location_b = WarehouseLocationFactory(code="B-01")
    location_c = WarehouseLocationFactory(code="C-01")

    movement_a_to_b = WarehouseMovementFactory(
        stock_product=product,
        location_from=location_a,
        location_to=location_b,
    )
    movement_b_to_c = WarehouseMovementFactory(
        stock_product=product,
        location_from=location_b,
        location_to=location_c,
    )

    # Filter by location_from
    response = client.get(f"warehouse-movements?location_from_id={location_a.pk}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["data"][0]["id"] == movement_a_to_b.pk

    # Filter by location_to
    response = client.get(f"warehouse-movements?location_to_id={location_c.pk}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["data"][0]["id"] == movement_b_to_c.pk


def test_get_warehouse_movements_api_filters_by_worker(db, client):
    product = StockProductFactory()
    location = WarehouseLocationFactory()
    worker1 = UserFactory(username="worker1")
    worker2 = UserFactory(username="worker2")

    movement1 = WarehouseMovementFactory(
        stock_product=product,
        location_to=location,
        worker=worker1,
    )
    WarehouseMovementFactory(
        stock_product=product,
        location_to=location,
        worker=worker2,
    )

    response = client.get(f"warehouse-movements?worker_id={worker1.pk}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["data"][0]["id"] == movement1.pk
    assert payload["data"][0]["worker_username"] == "worker1"


def test_get_warehouse_movements_api_includes_batch_barcode(db, client):
    from apps.warehouse.tests.factories.packaging import BatchFactory
    from apps.warehouse.models.barcode import BarcodeType

    product = StockProductFactory()
    location = WarehouseLocationFactory()
    batch = BatchFactory()

    # Add a barcode to the batch using the mixin method
    batch.attach_barcode(
        code="BATCH-123", barcode_type=BarcodeType.CUSTOM, is_primary=True
    )

    WarehouseMovementFactory(
        stock_product=product,
        location_to=location,
        batch=batch,
    )

    response = client.get("warehouse-movements")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["data"][0]["batch_id"] == batch.pk
    assert payload["data"][0]["batch_barcode"] == "BATCH-123"


def test_get_recent_warehouse_movements_api_returns_latest_eight(db, client):
    product = StockProductFactory()
    location = WarehouseLocationFactory()
    now = timezone.now()

    newest_movement = None
    for i in range(12):
        movement = WarehouseMovementFactory(
            stock_product=product,
            location_to=location,
            amount=Decimal(i + 1),
        )
        WarehouseMovement.objects.filter(pk=movement.pk).update(
            moved_at=now - timedelta(minutes=i)
        )
        if i == 0:
            newest_movement = movement

    response = client.get("recent-warehouse-movements")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert len(payload) == 8
    assert payload[0]["id"] == newest_movement.pk
    assert payload[0]["amount"] == "1.0000"
    assert payload[-1]["amount"] == "8.0000"


def test_get_warehouse_movements_api_handles_null_locations(db, client):
    product = StockProductFactory()

    # Movement with null location_from (e.g., initial stock entry)
    WarehouseMovementFactory(
        stock_product=product,
        location_from=None,
        location_to=WarehouseLocationFactory(code="A-01"),
    )

    response = client.get("warehouse-movements")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["data"][0]["location_from_code"] is None
    assert payload["data"][0]["location_to_code"] == "A-01"


def test_get_warehouse_movements_api_combines_multiple_filters(db, client):
    product1 = StockProductFactory(code="MULTI-001")
    product2 = StockProductFactory(code="MULTI-002")
    location_a = WarehouseLocationFactory(code="A-01")
    location_b = WarehouseLocationFactory(code="B-01")
    worker1 = UserFactory(username="worker1")
    UserFactory(username="worker2")
    now = timezone.now()

    # Movement matching all filters
    movement_match = WarehouseMovementFactory(
        stock_product=product1,
        location_from=location_a,
        location_to=location_b,
        worker=worker1,
    )
    WarehouseMovement.objects.filter(pk=movement_match.pk).update(moved_at=now)

    # Movements not matching all filters
    WarehouseMovementFactory(
        stock_product=product2,  # wrong product
        location_from=location_a,
        location_to=location_b,
        worker=worker1,
    )
    WarehouseMovementFactory(
        stock_product=product1,
        location_from=location_b,  # wrong location_from
        location_to=location_b,
        worker=worker1,
    )
    movement_old = WarehouseMovementFactory(
        stock_product=product1,
        location_from=location_a,
        location_to=location_b,
        worker=worker1,
    )
    WarehouseMovement.objects.filter(pk=movement_old.pk).update(
        moved_at=now - timedelta(days=2)  # too old
    )

    from urllib.parse import quote

    from_date = (now - timedelta(days=1)).isoformat()
    response = client.get(
        f"warehouse-movements?"
        f"stock_product_id={product1.pk}&"
        f"location_from_id={location_a.pk}&"
        f"location_to_id={location_b.pk}&"
        f"worker_id={worker1.pk}&"
        f"from_date={quote(from_date)}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["data"][0]["id"] == movement_match.pk
