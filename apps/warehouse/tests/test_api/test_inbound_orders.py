from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.inbound_orders import routes
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.models.orders import InboundOrderState
from apps.warehouse.tests.factories.customer import CustomerFactory
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


def test_get_inbound_order_audits_formats_transition_state_labels(db) -> None:
    client = TestClient(routes)
    order = InboundOrderFactory.it(state=InboundOrderState.DRAFT)

    audit_service.add_entry(
        order,
        action=AuditAction.TRANSITION,
        reason=AuditMessages.INBOUND_ORDER_STATE_CHANGED.CS.format(
            old_state=InboundOrderState.DRAFT,
            new_state=InboundOrderState.RECEIVING,
        ),
        changes={
            "state": {
                "old": InboundOrderState.DRAFT,
                "new": InboundOrderState.RECEIVING,
            }
        },
    )

    res = client.get(f"/{order.code}/audits")

    assert res.status_code == 200
    data = res.json()["data"]
    assert data[0]["reason"] == (
        "Stav příchozí objednávky se změnil z 'Draft' na 'Receiving'"
    )
    assert data[0]["changes"]["state"] == {"old": "Draft", "new": "Receiving"}


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
    self_customer = CustomerFactory(is_self=True)

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
    assert data["invoice"]["customer"]["code"] == self_customer.code
    assert data["invoice"]["payment_method"]["name"] == "Bank transfer"
    assert data["invoice"]["document"] is None


def test_store_inbound_order_invoice_stores_uploaded_document(
    db, settings, tmp_path
) -> None:
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"

    client = TestClient(routes)
    order = InboundOrderFactory.it()
    self_customer = CustomerFactory(is_self=True)

    res = client.post(
        f"/{order.code}/invoice",
        data={
            "code": "INV-POST-0002",
            "issued_date": "2026-04-01",
            "due_date": "2026-04-15",
            "payment_method_name": "Bank transfer",
            "taxable_supply_date": "2026-04-01",
            "currency": "CZK",
        },
        FILES={
            "invoice_file": SimpleUploadedFile(
                "invoice.pdf",
                b"%PDF-1.4 uploaded by api",
                content_type="application/pdf",
            )
        },
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["invoice"]["code"] == "INV-POST-0002"
    assert data["invoice"]["customer"]["code"] == self_customer.code
    assert data["invoice"]["document"]["name"] == "invoice.pdf"
    assert data["invoice"]["document"]["url"].endswith("invoice.pdf")


def test_store_inbound_order_invoice_replaces_existing_document(
    db, settings, tmp_path
) -> None:
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"

    self_customer = CustomerFactory(is_self=True)
    invoice = InvoiceFactory.it(code="INV-POST-0003")
    invoice.document.save(
        "old.pdf",
        SimpleUploadedFile(
            "old.pdf",
            b"%PDF-1.4 old document",
            content_type="application/pdf",
        ),
        save=True,
    )
    order = InboundOrderFactory.it(invoice=invoice)
    client = TestClient(routes)

    res = client.post(
        f"/{order.code}/invoice",
        data={
            "code": "INV-POST-0003",
            "issued_date": "2026-04-01",
            "due_date": "2026-04-15",
            "payment_method_name": "Bank transfer",
            "taxable_supply_date": "2026-04-01",
            "currency": "CZK",
        },
        FILES={
            "invoice_file": SimpleUploadedFile(
                "new.pdf",
                b"%PDF-1.4 replacement document",
                content_type="application/pdf",
            )
        },
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["invoice"]["code"] == "INV-POST-0003"
    assert data["invoice"]["customer"]["code"] == self_customer.code
    assert data["invoice"]["document"]["name"] == "new.pdf"
    assert data["invoice"]["document"]["url"].endswith("new.pdf")


def test_update_inbound_order_item_without_index_keeps_existing_index(db) -> None:
    client = TestClient(routes)
    order = InboundOrderFactory.it()
    product = StockProductFactory()

    add_res = client.post(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 2,
            "total_price": 20,
            "index": 3,
        },
    )
    assert add_res.status_code == 200
    assert add_res.json()["data"]["index"] == 3

    update_res = client.put(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 4,
            "total_price": 48,
        },
    )

    assert update_res.status_code == 200
    assert update_res.json()["data"]["index"] == 3
