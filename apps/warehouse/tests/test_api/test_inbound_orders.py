from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.inbound_orders import routes
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.tests.factories.order import InboundOrderFactory, InvoiceFactory
from apps.warehouse.tests.factories.order import InboundOrderItemFactory
from apps.warehouse.tests.factories.product import StockProductFactory


def test_get_inbound_order_audits(db) -> None:
    client = TestClient(routes)
    order = InboundOrderFactory.it()

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


def test_get_inbound_orders_filter_by_stock_product_code(db) -> None:
    client = TestClient(routes)
    shared_product = StockProductFactory()
    other_product = StockProductFactory()

    matching_order = InboundOrderFactory.it(code="ORD-MATCH-0001")
    non_matching_order = InboundOrderFactory.it(code="ORD-OTHER-0001")

    InboundOrderItemFactory(order=matching_order, stock_product=shared_product)
    InboundOrderItemFactory(order=non_matching_order, stock_product=other_product)

    res = client.get(f"/?stock_product_code={shared_product.code}")

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["code"] == matching_order.code


def test_get_inbound_orders_filter_by_stock_product_code_and_search_term(db) -> None:
    client = TestClient(routes)
    shared_product = StockProductFactory()
    secondary_product = StockProductFactory()

    matching_order = InboundOrderFactory.it(code="ORD-MATCH-0002")
    same_product_different_search = InboundOrderFactory.it(code="ORD-DIFF-0002")
    same_search_different_product = InboundOrderFactory.it(code="ORD-MATCH-0999")

    InboundOrderItemFactory(order=matching_order, stock_product=shared_product)
    InboundOrderItemFactory(
        order=same_product_different_search, stock_product=shared_product
    )
    InboundOrderItemFactory(
        order=same_search_different_product, stock_product=secondary_product
    )

    res = client.get(
        f"/?stock_product_code={shared_product.code}&search_term=match-0002"
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["code"] == matching_order.code


def test_get_inbound_order_includes_invoice(db, settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"

    invoice = InvoiceFactory.it(code="INV-API-0001")
    invoice.document.save(
        "invoice.pdf",
        SimpleUploadedFile(
            "invoice.pdf",
            b"%PDF-1.4 api test invoice",
            content_type="application/pdf",
        ),
        save=True,
    )
    order = InboundOrderFactory.it(invoice=invoice)
    client = TestClient(routes)

    res = client.get(f"/{order.code}")

    assert res.status_code == 200
    invoice_data = res.json()["data"]["invoice"]
    assert invoice_data["code"] == invoice.code
    assert invoice_data["payment_method"]["name"] == invoice.payment_method.name
    assert invoice_data["document"]["name"] == "invoice.pdf"
    assert invoice_data["document"]["url"].endswith("invoice.pdf")


def test_store_inbound_order_invoice(db) -> None:
    client = TestClient(routes)
    order = InboundOrderFactory.it()

    res = client.post(
        f"/{order.code}/invoice",
        data={
            "code": "INV-POST-0001",
            "issued_date": "2026-04-01",
            "due_date": "2026-04-15",
            "payment_method_name": "Bank transfer",
            "external_code": "POST-EXT-001",
            "taxable_supply_date": "2026-04-01",
            "currency": "CZK",
            "note": "Stored through API",
        },
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["invoice"]["code"] == "INV-POST-0001"
    assert data["invoice"]["payment_method"]["name"] == "Bank transfer"
    assert data["invoice"]["document"] is None
