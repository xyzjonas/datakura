from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.outbound_orders import routes
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.models.orders import OutboundOrderState
from apps.warehouse.models.warehouse import OutboundWarehouseOrder
from apps.warehouse.tests.factories.order import (
    InvoiceFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import (
    StockProductFactory,
    StockProductPriceCustomerFactory,
)


def test_get_outbound_order_audits(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()

    older_log = audit_service.add_entry(
        order,
        action=AuditAction.CREATE,
        reason=AuditMessages.ORDER_CREATED.CS,
    )
    newer_log = audit_service.add_entry(
        order,
        action=AuditAction.UPDATE,
        reason=AuditMessages.ORDER_UPDATED.CS,
    )

    now = timezone.now()
    AuditLog.objects.filter(pk=older_log.pk).update(created=now - timedelta(minutes=10))  # type: ignore
    AuditLog.objects.filter(pk=newer_log.pk).update(created=now)  # type: ignore

    res = client.get(f"/{order.code}/audits")

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 2
    assert data[0]["source"] == "audit"
    assert data[0]["action"] == AuditAction.UPDATE
    assert data[1]["action"] == AuditAction.CREATE


def test_get_outbound_orders_filter_by_stock_product_code(db) -> None:
    client = TestClient(routes)
    shared_product = StockProductFactory()
    other_product = StockProductFactory()

    matching_order = OutboundOrderFactory.it(code="SORD-MATCH-0001")
    non_matching_order = OutboundOrderFactory.it(code="SORD-OTHER-0001")

    OutboundOrderItemFactory(order=matching_order, stock_product=shared_product)
    OutboundOrderItemFactory(order=non_matching_order, stock_product=other_product)

    res = client.get(f"/?stock_product_code={shared_product.code}")

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["code"] == matching_order.code


def test_get_outbound_order_includes_invoice(db, settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"

    invoice = InvoiceFactory.it(code="INV-API-S-0001")
    invoice.document.save(
        "invoice.pdf",
        SimpleUploadedFile(
            "invoice.pdf",
            b"%PDF-1.4 api test invoice",
            content_type="application/pdf",
        ),
        save=True,
    )
    order = OutboundOrderFactory.it(invoice=invoice)
    client = TestClient(routes)

    res = client.get(f"/{order.code}")

    assert res.status_code == 200
    invoice_data = res.json()["data"]["invoice"]
    assert invoice_data["code"] == invoice.code
    assert invoice_data["payment_method"]["name"] == invoice.payment_method.name
    assert invoice_data["document"]["name"] == "invoice.pdf"
    assert invoice_data["document"]["url"].endswith("invoice.pdf")


def test_store_outbound_order_invoice(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()

    res = client.post(
        f"/{order.code}/invoice",
        data={
            "code": "INV-POST-S-0001",
            "issued_date": "2026-04-01",
            "due_date": "2026-04-15",
            "payment_method_name": "Bank transfer",
            "external_code": "POST-EXT-S-001",
            "taxable_supply_date": "2026-04-01",
            "currency": "CZK",
            "note": "Stored through API",
        },
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["invoice"]["code"] == "INV-POST-S-0001"
    assert data["invoice"]["payment_method"]["name"] == "Bank transfer"
    assert data["invoice"]["document"] is None


def test_add_update_remove_outbound_order_item_keeps_index(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    product = StockProductFactory(base_price=150, purchase_price=90)
    StockProductPriceCustomerFactory(
        product=product,
        customer=order.customer,
        discount_percent=20,
    )

    add_res = client.post(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 2,
            "total_price": 10,
            "index": 0,
        },
    )
    assert add_res.status_code == 200
    assert add_res.json()["data"]["index"] == 0
    pricing_details = add_res.json()["data"]["pricing_details"]
    assert pricing_details["base_price"] == 150.0
    assert pricing_details["suggested_unit_price"] == 120.0
    assert pricing_details["avg_purchase_price"] == 90.0
    assert pricing_details["source"] == "CUSTOMER_OVERRIDE"

    update_res = client.put(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 2,
            "total_price": 10,
            "index": 5,
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["index"] == 5
    assert update_res.json()["data"]["pricing_details"]["selected_unit_price"] == 5.0

    delete_res = client.delete(f"/{order.code}/items/{product.code}")
    assert delete_res.status_code == 200
    assert delete_res.json()["success"] is True


def test_get_outbound_order_contains_item_pricing_details(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    product = StockProductFactory(base_price=120, purchase_price=100)
    OutboundOrderItemFactory(
        order=order, stock_product=product, amount=2, unit_price=130
    )

    response = client.get(f"/{order.code}")

    assert response.status_code == 200
    item = response.json()["data"]["items"][0]
    assert item["pricing_details"]["base_price"] == 120.0
    assert item["pricing_details"]["selected_unit_price"] == 130.0
    assert item["pricing_details"]["margin_amount"] == 30.0


def test_transition_outbound_order_next_creates_warehouse_order(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.DRAFT)
    product = StockProductFactory()
    OutboundOrderItemFactory(order=order, stock_product=product, amount=2)

    res = client.post(f"/{order.code}/transition", json={"action": "next"})

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["state"] == OutboundOrderState.PICKING
    assert len(data["warehouse_orders"]) == 1
    assert data["warehouse_orders"][0]["order_code"] == order.code
    assert OutboundWarehouseOrder.objects.filter(order__code=order.code).count() == 1


def test_transition_outbound_order_cancel_action(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.DRAFT)

    res = client.post(f"/{order.code}/transition", json={"action": "cancel"})

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["state"] == OutboundOrderState.CANCELLED
