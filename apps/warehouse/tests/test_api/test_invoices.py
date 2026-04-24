from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.invoices import routes
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.models.orders import OutboundOrderState
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
    InvoiceFactory,
    InvoicePaymentMethodFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import WarehouseOrderOutFactory
from apps.warehouse.models.warehouse import OutboundWarehouseOrderState


def test_get_outbound_invoices_returns_only_outbound_invoices_sorted_by_created(
    db,
) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()
    newer_invoice = InvoiceFactory.it(customer=customer, supplier=CustomerFactory())
    older_invoice = InvoiceFactory.it(customer=customer, supplier=CustomerFactory())
    inbound_only_invoice = InvoiceFactory.it(customer=None, supplier=CustomerFactory())

    OutboundOrderFactory.it(customer=customer, invoice=newer_invoice)
    OutboundOrderFactory.it(customer=customer, invoice=older_invoice)
    InboundOrderFactory.it(invoice=inbound_only_invoice)

    now = timezone.now()
    type(newer_invoice).objects.filter(pk=newer_invoice.pk).update(created=now)
    type(older_invoice).objects.filter(pk=older_invoice.pk).update(
        created=now - timedelta(days=1)
    )

    response = client.get("/outbound")

    assert response.status_code == 200
    data = response.json()["data"]
    assert [invoice["code"] for invoice in data] == [
        newer_invoice.code,
        older_invoice.code,
    ]


def test_get_inbound_invoices_returns_only_inbound_invoices_sorted_by_created(
    db,
) -> None:
    client = TestClient(routes)
    supplier = CustomerFactory()
    newer_invoice = InvoiceFactory.it(customer=None, supplier=supplier)
    older_invoice = InvoiceFactory.it(customer=None, supplier=supplier)
    outbound_only_invoice = InvoiceFactory.it(
        customer=CustomerFactory(), supplier=supplier
    )

    InboundOrderFactory.it(invoice=newer_invoice, supplier=supplier)
    InboundOrderFactory.it(invoice=older_invoice, supplier=supplier)
    OutboundOrderFactory.it(invoice=outbound_only_invoice)

    now = timezone.now()
    type(newer_invoice).objects.filter(pk=newer_invoice.pk).update(created=now)
    type(older_invoice).objects.filter(pk=older_invoice.pk).update(
        created=now - timedelta(days=1)
    )

    response = client.get("/inbound")

    assert response.status_code == 200
    data = response.json()["data"]
    assert [invoice["code"] for invoice in data] == [
        newer_invoice.code,
        older_invoice.code,
    ]


def test_create_outbound_invoice_links_selected_orders(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()
    supplier = CustomerFactory(is_self=True)
    future_due_date = timezone.localdate() + timedelta(days=14)
    first_order = OutboundOrderFactory.it(
        customer=customer,
        currency="CZK",
        invoice=None,
        state=OutboundOrderState.SUBMITTED,
    )
    second_order = OutboundOrderFactory.it(
        customer=customer,
        currency="CZK",
        invoice=None,
        state=OutboundOrderState.SUBMITTED,
    )
    first_product = StockProductFactory()
    second_product = StockProductFactory()
    WarehouseOrderOutFactory.it(
        order=first_order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )
    WarehouseOrderOutFactory.it(
        order=second_order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )
    OutboundOrderItemFactory(
        order=first_order,
        stock_product=first_product,
        amount=2,
        unit_price=50,
        total_price=100,
        index=0,
    )
    OutboundOrderItemFactory(
        order=second_order,
        stock_product=second_product,
        amount=3,
        unit_price=40,
        total_price=120,
        index=0,
    )

    response = client.post(
        "/outbound",
        json={
            "order_codes": [first_order.code, second_order.code],
            "issued_date": timezone.localdate().isoformat(),
            "due_date": future_due_date.isoformat(),
            "payment_method_name": "Bank transfer",
            "external_code": "EXT-INV-001",
            "taxable_supply_date": timezone.localdate().isoformat(),
            "paid_date": None,
            "note": "Auto generated invoice",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["code"].startswith("SINV")
    assert data["customer"]["code"] == customer.code
    assert data["supplier"]["code"] == supplier.code
    assert data["currency"] == "CZK"
    assert data["payment_method"]["name"] == "Bank transfer"
    assert [order["code"] for order in data["outbound_orders"]] == [
        first_order.code,
        second_order.code,
    ]
    assert (
        data["outbound_orders"][0]["items"][0]["product"]["code"] == first_product.code
    )
    assert (
        data["outbound_orders"][1]["items"][0]["product"]["code"] == second_product.code
    )

    first_order.refresh_from_db()
    second_order.refresh_from_db()
    assert first_order.invoice_id is not None
    assert first_order.invoice_id == second_order.invoice_id
    assert first_order.state == OutboundOrderState.INVOICED
    assert second_order.state == OutboundOrderState.INVOICED


def test_create_outbound_invoice_uses_customer_default_payment_method(db) -> None:
    client = TestClient(routes)
    payment_method = InvoicePaymentMethodFactory.it(name="Bank transfer")
    customer = CustomerFactory(default_payment_method=payment_method)
    supplier = CustomerFactory(is_self=True)
    order = OutboundOrderFactory.it(
        customer=customer,
        currency="CZK",
        invoice=None,
        state=OutboundOrderState.SUBMITTED,
    )
    WarehouseOrderOutFactory.it(
        order=order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )

    response = client.post(
        "/outbound",
        json={
            "order_codes": [order.code],
            "issued_date": "2026-04-01",
            "due_date": "2026-04-15",
            "taxable_supply_date": "2026-04-01",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["payment_method"]["name"] == payment_method.name
    assert data["supplier"]["code"] == supplier.code


def test_create_outbound_invoice_rejects_mixed_customers(db) -> None:
    client = TestClient(routes)
    first_order = OutboundOrderFactory.it(
        invoice=None,
        currency="CZK",
        state=OutboundOrderState.SUBMITTED,
    )
    second_order = OutboundOrderFactory.it(
        invoice=None,
        currency="CZK",
        state=OutboundOrderState.SUBMITTED,
    )
    WarehouseOrderOutFactory.it(
        order=first_order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )
    WarehouseOrderOutFactory.it(
        order=second_order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )

    with pytest.raises(WarehouseItemBadRequestError, match="same customer"):
        client.post(
            "/outbound",
            json={
                "order_codes": [first_order.code, second_order.code],
                "issued_date": "2026-04-01",
                "due_date": "2026-04-15",
                "payment_method_name": "Bank transfer",
                "taxable_supply_date": "2026-04-01",
            },
        )


def test_create_outbound_invoice_requires_completed_warehouse_order(db) -> None:
    client = TestClient(routes)
    CustomerFactory(is_self=True)
    order = OutboundOrderFactory.it(
        invoice=None,
        currency="CZK",
        state=OutboundOrderState.SUBMITTED,
    )

    with pytest.raises(
        WarehouseItemBadRequestError, match="completed warehouse orders"
    ):
        client.post(
            "/outbound",
            json={
                "order_codes": [order.code],
                "issued_date": "2026-04-01",
                "due_date": "2026-04-15",
                "payment_method_name": "Bank transfer",
                "taxable_supply_date": "2026-04-01",
            },
        )


def test_get_invoice_returns_grouped_outbound_orders(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()
    invoice = InvoiceFactory.it(customer=customer, supplier=None, currency="CZK")
    order = OutboundOrderFactory.it(customer=customer, currency="CZK", invoice=invoice)
    product = StockProductFactory()
    OutboundOrderItemFactory(
        order=order,
        stock_product=product,
        amount=1,
        unit_price=99,
        total_price=99,
        index=0,
    )

    response = client.get(f"/{invoice.code}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["code"] == invoice.code
    assert len(data["outbound_orders"]) == 1
    assert data["outbound_orders"][0]["code"] == order.code


def test_update_invoice_moves_outbound_orders_to_waiting_for_payment(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()
    supplier = CustomerFactory(is_self=True)
    invoice = InvoiceFactory.it(customer=customer, supplier=supplier, currency="CZK")
    order = OutboundOrderFactory.it(
        customer=customer,
        currency="CZK",
        invoice=invoice,
        state=OutboundOrderState.INVOICED,
    )
    WarehouseOrderOutFactory.it(
        order=order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )
    payment_method = invoice.payment_method
    past_due_date = timezone.localdate() - timedelta(days=2)

    response = client.put(
        f"/{invoice.code}",
        data={
            "customer_code": customer.code,
            "supplier_code": supplier.code,
            "code": invoice.code,
            "issued_date": timezone.localdate().isoformat(),
            "due_date": past_due_date.isoformat(),
            "payment_method_name": payment_method.name,
            "external_code": invoice.external_code,
            "taxable_supply_date": timezone.localdate().isoformat(),
            "currency": "CZK",
            "note": "Past due invoice",
        },
    )

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.state == OutboundOrderState.WAITING_FOR_PAYMENT
    assert response.json()["data"]["due_date"] == past_due_date.isoformat()


def test_update_invoice_accepts_multipart_put_with_document(
    db, settings, tmp_path, user
) -> None:
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"

    client = Client()
    client.force_login(user)
    customer = CustomerFactory()
    supplier = CustomerFactory(is_self=True)
    invoice = InvoiceFactory.it(customer=customer, supplier=supplier, currency="CZK")
    order = OutboundOrderFactory.it(
        customer=customer,
        currency="CZK",
        invoice=invoice,
        state=OutboundOrderState.INVOICED,
    )
    WarehouseOrderOutFactory.it(
        order=order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )

    response = client.generic(
        "PUT",
        f"/api/v1/invoices/{invoice.code}",
        encode_multipart(
            BOUNDARY,
            {
                "customer_code": customer.code,
                "supplier_code": supplier.code,
                "code": invoice.code,
                "issued_date": "2026-04-01",
                "due_date": "2026-04-15",
                "payment_method_name": invoice.payment_method.name,
                "taxable_supply_date": "2026-04-01",
                "currency": "CZK",
                "note": "Updated over multipart PUT",
                "invoice_file": SimpleUploadedFile(
                    "invoice.pdf",
                    b"%PDF-1.4 updated over multipart PUT",
                    content_type="application/pdf",
                ),
            },
        ),
        content_type=MULTIPART_CONTENT,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["code"] == invoice.code
    assert data["note"] == "Updated over multipart PUT"
    assert data["document"]["name"] == "invoice.pdf"
    assert data["document"]["url"].endswith("invoice.pdf")


def test_mark_invoice_paid_moves_outbound_orders_to_completed_paid(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()
    supplier = CustomerFactory(is_self=True)
    invoice = InvoiceFactory.it(
        customer=customer,
        supplier=supplier,
        currency="CZK",
        paid_date=None,
    )
    order = OutboundOrderFactory.it(
        customer=customer,
        currency="CZK",
        invoice=invoice,
        state=OutboundOrderState.WAITING_FOR_PAYMENT,
    )
    WarehouseOrderOutFactory.it(
        order=order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )

    response = client.post(
        f"/{invoice.code}/mark-paid",
        json={"paid_date": timezone.localdate().isoformat()},
    )

    assert response.status_code == 200
    order.refresh_from_db()
    invoice.refresh_from_db()
    assert invoice.paid_date == timezone.localdate()
    assert order.state == OutboundOrderState.COMPLETED_PAID
    assert response.json()["data"]["paid_date"] == timezone.localdate().isoformat()


def test_get_invoice_returns_grouped_inbound_orders(db) -> None:
    client = TestClient(routes)
    supplier = CustomerFactory()
    customer = CustomerFactory(is_self=True)
    invoice = InvoiceFactory.it(customer=customer, supplier=supplier, currency="CZK")
    order = InboundOrderFactory.it(supplier=supplier, currency="CZK", invoice=invoice)
    product = StockProductFactory()
    InboundOrderItemFactory(
        order=order,
        stock_product=product,
        amount=2,
        unit_price=75,
        total_price=150,
        index=0,
    )

    response = client.get(f"/{invoice.code}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["code"] == invoice.code
    assert data["outbound_orders"] == []
    assert len(data["inbound_orders"]) == 1
    assert data["inbound_orders"][0]["code"] == order.code
    assert data["inbound_orders"][0]["items"][0]["product"]["name"] == product.name


def test_get_invoice_pdf_returns_pdf_document(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory(
        name="ACME s.r.o.",
        street="Ulice 1",
        postal_code="11000",
        city="Praha",
        identification="12345678",
        tax_identification="CZ12345678",
    )
    supplier = CustomerFactory(
        name="Dodavatel s.r.o.",
        street="Dlouha 2",
        postal_code="60200",
        city="Brno",
        identification="87654321",
        tax_identification="CZ87654321",
    )
    invoice = InvoiceFactory.it(customer=customer, supplier=supplier, currency="CZK")
    order = OutboundOrderFactory.it(customer=customer, currency="CZK", invoice=invoice)
    product = StockProductFactory()
    OutboundOrderItemFactory(
        order=order, stock_product=product, total_price=100, unit_price=100
    )

    response = client.get(f"/{invoice.code}/pdf")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
