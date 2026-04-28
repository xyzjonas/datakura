from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.outbound_orders import routes
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.models.orders import OutboundOrderState
from apps.warehouse.models.warehouse import (
    Batch,
    InboundWarehouseOrderState,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderItem,
    OutboundWarehouseOrderState,
)
from apps.warehouse.tests.factories.order import (
    InvoiceFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.packaging import PackageTypeFactory
from apps.warehouse.tests.factories.product import (
    StockProductFactory,
    StockProductPriceCustomerFactory,
)
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
    WarehouseOrderOutFactory,
)
import pytest


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


def test_get_outbound_order_audits_formats_transition_state_labels(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.DRAFT)

    audit_service.add_entry(
        order,
        action=AuditAction.TRANSITION,
        reason=AuditMessages.OUTBOUND_ORDER_STATE_CHANGED.CS.format(
            old_state=OutboundOrderState.DRAFT,
            new_state=OutboundOrderState.PICKING,
        ),
        changes={
            "state": {
                "old": OutboundOrderState.DRAFT,
                "new": OutboundOrderState.PICKING,
            }
        },
    )

    res = client.get(f"/{order.code}/audits")

    assert res.status_code == 200
    data = res.json()["data"]
    assert (
        data[0]["reason"] == "Stav vydané objednávky se změnil z 'Draft' na 'Picking'"
    )
    assert data[0]["changes"]["state"] == {"old": "Draft", "new": "Picking"}


@pytest.mark.parametrize(
    ("query_param", "expected_value"),
    [("stock_product_code", "product"), ("customer_code", "customer")],
)
def test_get_outbound_orders_supports_filtering(
    db, query_param: str, expected_value: str
) -> None:
    client = TestClient(routes)
    shared_product = StockProductFactory()
    other_product = StockProductFactory()
    matching_customer = CustomerFactory()
    other_customer = CustomerFactory()

    matching_order = OutboundOrderFactory.it(
        code="SORD-MATCH-0001", customer=matching_customer
    )
    non_matching_order = OutboundOrderFactory.it(
        code="SORD-OTHER-0001",
        customer=other_customer,
    )

    OutboundOrderItemFactory(order=matching_order, stock_product=shared_product)
    OutboundOrderItemFactory(order=non_matching_order, stock_product=other_product)

    query_value = (
        shared_product.code if expected_value == "product" else matching_customer.code
    )
    res = client.get(f"/?{query_param}={query_value}")

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
    order = OutboundOrderFactory.it(state=OutboundOrderState.SENT)
    WarehouseOrderOutFactory.it(
        order=order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )
    future_due_date = timezone.localdate() + timedelta(days=14)

    res = client.post(
        f"/{order.code}/invoice",
        data={
            "code": "INV-POST-S-0001",
            "issued_date": timezone.localdate().isoformat(),
            "due_date": future_due_date.isoformat(),
            "payment_method_name": "Bank transfer",
            "external_code": "POST-EXT-S-001",
            "taxable_supply_date": timezone.localdate().isoformat(),
            "currency": "CZK",
            "note": "Stored through API",
        },
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["invoice"]["code"] == "INV-POST-S-0001"
    assert data["invoice"]["payment_method"]["name"] == "Bank transfer"
    assert data["invoice"]["document"] is None
    assert data["state"] == OutboundOrderState.get_label(OutboundOrderState.INVOICED)


def test_add_update_remove_outbound_order_item_keeps_index(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    product = StockProductFactory(base_price=150, purchase_price=90)
    StockProductPriceCustomerFactory(
        product=product,
        customer=order.customer,
        fixed_price=120,
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


def test_update_outbound_order_item_without_index_keeps_existing_index(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    product = StockProductFactory()

    add_res = client.post(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 3,
            "total_price": 30,
            "index": 4,
        },
    )
    assert add_res.status_code == 200
    assert add_res.json()["data"]["index"] == 4

    update_res = client.put(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 5,
            "total_price": 50,
        },
    )

    assert update_res.status_code == 200
    assert update_res.json()["data"]["index"] == 4


def test_add_outbound_order_item_with_desired_package_and_batch(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    product = StockProductFactory()
    package = PackageTypeFactory(unit_of_measure=product.unit_of_measure, amount=2)
    batch = Batch.objects.create()
    batch.attach_barcode("BATCH-OUT-001", is_primary=True)

    response = client.post(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 4,
            "total_price": 40,
            "desired_package_type_name": package.name,
            "desired_batch_code": "BATCH-OUT-001",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["desired_package_type_name"] == package.name
    assert data["desired_batch_code"] == "BATCH-OUT-001"


def test_transition_outbound_order_materializes_warehouse_order_items(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.DRAFT)
    product = StockProductFactory()
    package = PackageTypeFactory(unit_of_measure=product.unit_of_measure, amount=2)
    batch = Batch.objects.create()
    batch.attach_barcode("BATCH-OUT-002", is_primary=True)
    OutboundOrderItemFactory(
        order=order,
        stock_product=product,
        amount=10,
        desired_package_type=package,
        desired_batch=batch,
    )

    inbound_order = InboundWarehouseOrderFactory(
        state=InboundWarehouseOrderState.PENDING
    )
    location = WarehouseLocationFactory(is_putaway=False)
    WarehouseItemFactory(
        order_in=inbound_order,
        stock_product=product,
        amount=6,
        package_type=package,
        batch=batch,
        location=location,
    )
    WarehouseItemFactory(
        order_in=inbound_order,
        stock_product=product,
        amount=4,
        package_type=package,
        batch=batch,
        location=location,
    )

    res = client.post(f"/{order.code}/transition", json={"action": "next"})

    assert res.status_code == 200
    warehouse_order = OutboundWarehouseOrder.objects.get(order=order)
    items = list(
        OutboundWarehouseOrderItem.objects.filter(
            warehouse_order=warehouse_order
        ).order_by("amount")
    )
    assert [float(item.amount) for item in items] == [4.0, 6.0]
    assert all(item.desired_package_type == package for item in items)
    assert all(item.desired_batch == batch for item in items)


def test_transition_outbound_order_materializes_items_from_pending_inbound_putaway_stock(
    db,
) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.DRAFT)
    product = StockProductFactory()
    OutboundOrderItemFactory(
        order=order,
        stock_product=product,
        amount=10,
    )

    inbound_order = InboundWarehouseOrderFactory(
        state=InboundWarehouseOrderState.PENDING
    )
    putaway_location = WarehouseLocationFactory(is_putaway=True)
    WarehouseItemFactory(
        order_in=inbound_order,
        stock_product=product,
        amount=6,
        location=putaway_location,
    )
    WarehouseItemFactory(
        order_in=inbound_order,
        stock_product=product,
        amount=4,
        location=putaway_location,
    )

    res = client.post(f"/{order.code}/transition", json={"action": "next"})

    assert res.status_code == 200
    warehouse_order = OutboundWarehouseOrder.objects.get(order=order)
    items = list(
        OutboundWarehouseOrderItem.objects.filter(
            warehouse_order=warehouse_order
        ).order_by("amount")
    )
    assert [float(item.amount) for item in items] == [4.0, 6.0]


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
    assert data["state"] == OutboundOrderState.get_label(OutboundOrderState.PICKING)
    assert len(data["warehouse_orders"]) == 1
    assert data["warehouse_orders"][0]["order_code"] == order.code
    assert OutboundWarehouseOrder.objects.filter(order__code=order.code).count() == 1


def test_transition_outbound_order_next_skips_packing_and_shipping(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.PICKING)

    res = client.post(f"/{order.code}/transition", json={"action": "next"})

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["state"] == OutboundOrderState.get_label(OutboundOrderState.SENT)


def test_transition_outbound_order_cancel_action(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.DRAFT)

    res = client.post(f"/{order.code}/transition", json={"action": "cancel"})

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["state"] == OutboundOrderState.get_label(OutboundOrderState.CANCELLED)
