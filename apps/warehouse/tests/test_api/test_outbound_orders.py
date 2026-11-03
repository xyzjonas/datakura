from decimal import Decimal
from datetime import timedelta
from typing import cast

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.outbound_orders import routes
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.models.orders import (
    OutboundCalculationState,
    OutboundOrder,
    OutboundOrderItem,
    OutboundOrderState,
)
from apps.warehouse.models.product import PriceGroup
from apps.warehouse.models.warehouse import (
    Batch,
    InboundWarehouseOrderState,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderItem,
    OutboundWarehouseOrderState,
)
from apps.warehouse.tests.factories.order import (
    InvoiceFactory,
    OutboundCalculationFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.customer import (
    ContactPersonFactory,
    CustomerFactory,
)
from apps.warehouse.tests.factories.packaging import PackageTypeFactory
from apps.warehouse.tests.factories.settings import GlobalSettingsFactory
from apps.warehouse.tests.factories.product import (
    PriceGroupFactory,
    StockProductFactory,
    StockProductPriceCustomerFactory,
)
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    OutboundWarehouseOrderItemFactory,
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
    order = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)

    audit_service.add_entry(
        order,
        action=AuditAction.TRANSITION,
        reason=AuditMessages.OUTBOUND_ORDER_STATE_CHANGED.CS.format(
            old_state=OutboundOrderState.SUBMITTED,
            new_state=OutboundOrderState.PICKING,
        ),
        changes={
            "state": {
                "old": OutboundOrderState.SUBMITTED,
                "new": OutboundOrderState.PICKING,
            }
        },
    )

    res = client.get(f"/{order.code}/audits")

    assert res.status_code == 200
    data = res.json()["data"]
    assert (
        data[0]["reason"]
        == "Stav vydané objednávky se změnil z 'Submitted' na 'Picking'"
    )
    assert data[0]["changes"]["state"] == {"old": "Submitted", "new": "Picking"}


def test_create_outbound_order_starts_submitted_with_order_code(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()

    response = client.post(
        "",
        json={
            "external_code": "OUT-CALC-001",
            "description": "Order without a calculation",
            "note": "Direct order",
            "currency": "CZK",
            "customer_code": customer.code,
            "customer_name": customer.name,
            "requested_delivery_date": None,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["state"] == OutboundOrderState.get_label(OutboundOrderState.SUBMITTED)
    assert data["code"].startswith("OP")
    assert data["calculation_code"] is None

    order = OutboundOrder.objects.get(code=data["code"])
    assert order.state == OutboundOrderState.SUBMITTED
    assert not hasattr(order, "calculation")


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
        code="SORD-MATCH-0001",
        customer=matching_customer,
        state=OutboundOrderState.PICKING,
    )
    non_matching_order = OutboundOrderFactory.it(
        code="SORD-OTHER-0001",
        customer=other_customer,
        state=OutboundOrderState.PICKING,
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
    assert invoice_data["payment_method"]["name"] == str(invoice.payment_method)
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
        f"/{order.code}/items/0",
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

    delete_res = client.delete(f"/{order.code}/items/5")
    assert delete_res.status_code == 200
    assert delete_res.json()["success"] is True


def test_duplicate_product_items_update_and_remove_by_index(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    product = StockProductFactory()

    add1 = client.post(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 1,
            "total_price": 10,
        },
    )
    assert add1.status_code == 200
    index1 = add1.json()["data"]["index"]

    add2 = client.post(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 3,
            "total_price": 30,
        },
    )
    assert add2.status_code == 200
    index2 = add2.json()["data"]["index"]
    assert index2 != index1

    update_res = client.put(
        f"/{order.code}/items/{index2}",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 99,
            "total_price": 990,
            "index": index2,
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["amount"] == 99

    delete_res = client.delete(f"/{order.code}/items/{index1}")
    assert delete_res.status_code == 200
    assert delete_res.json()["success"] is True

    from apps.warehouse.models.orders import OutboundOrderItem

    assert OutboundOrderItem.objects.filter(order=order).count() == 1
    assert OutboundOrderItem.objects.get(order=order).index == 0


def test_add_outbound_order_item_pricing_details_explain_no_discount_product(
    db,
) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    order.customer.discount_group = cast(
        PriceGroup,
        PriceGroupFactory(discount_percent=20),
    )
    order.customer.save(update_fields=["discount_group", "changed"])
    product = StockProductFactory(base_price=150, purchase_price=90, no_discount=True)

    response = client.post(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 2,
            "total_price": 300,
            "index": 0,
        },
    )

    assert response.status_code == 200
    pricing_details = response.json()["data"]["pricing_details"]
    assert pricing_details["base_price"] == 150.0
    assert pricing_details["suggested_unit_price"] == 150.0
    assert pricing_details["discount_percent"] == 0.0
    assert pricing_details["source"] == "NO_DISCOUNT"
    assert "disabled" in pricing_details["reason"]


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
        f"/{order.code}/items/4",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 5,
            "total_price": 50,
        },
    )

    assert update_res.status_code == 200
    assert update_res.json()["data"]["index"] == 4


def test_update_outbound_order_item_syncs_open_warehouse_requirement(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.PICKING)
    product = StockProductFactory()
    source_item = OutboundOrderItemFactory.it(
        order=order,
        stock_product=product,
        amount=4,
        total_price=40,
        unit_price=10,
    )
    warehouse_order = WarehouseOrderOutFactory.it(
        order=order,
        state=OutboundWarehouseOrderState.PENDING,
    )
    requirement = OutboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        source_order_item=source_item,
        stock_product=product,
        amount=4,
    )

    response = client.put(
        f"/{order.code}/items/{source_item.index}",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 6,
            "total_price": 60,
            "index": source_item.index,
        },
    )

    assert response.status_code == 200
    requirement.refresh_from_db()
    source_item.refresh_from_db()
    assert float(source_item.amount) == 6.0
    assert float(requirement.amount) == 6.0
    assert requirement.warehouse_order_id == warehouse_order.id


def test_add_outbound_order_item_creates_child_warehouse_order_after_completed_pick(
    db,
) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.SENT)
    completed_warehouse_order = WarehouseOrderOutFactory.it(
        order=order,
        state=OutboundWarehouseOrderState.COMPLETED,
    )
    product = StockProductFactory.it()

    response = client.post(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 3,
            "total_price": 90,
            "index": 0,
        },
    )

    assert response.status_code == 200
    child_order = (
        OutboundWarehouseOrder.objects.filter(order=order)
        .exclude(pk=completed_warehouse_order.pk)
        .get()
    )
    assert child_order.primary_order_id == completed_warehouse_order.id
    child_requirement = OutboundWarehouseOrderItem.objects.get(
        warehouse_order=child_order,
        source_order_item__stock_product=product,
    )
    assert float(child_requirement.amount) == 3.0


def test_update_outbound_order_item_cannot_decrease_below_assigned_amount(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.PICKING)
    product = StockProductFactory()
    source_item = OutboundOrderItemFactory(
        order=order,
        stock_product=product,
        amount=4,
        total_price=40,
        unit_price=10,
    )
    warehouse_order = WarehouseOrderOutFactory.it(
        order=order,
        state=OutboundWarehouseOrderState.PENDING,
    )
    assigned_item = WarehouseItemFactory.it(stock_product=product, amount=4)
    OutboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        source_order_item=source_item,
        stock_product=product,
        amount=4,
        warehouse_item=assigned_item,
    )

    with pytest.raises(
        WarehouseItemBadRequestError,
        match="Assigned warehouse items prevent decreasing amount below already assigned quantity",
    ):
        client.put(
            f"/{order.code}/items/{source_item.index}",
            json={
                "product_code": product.code,
                "product_name": product.name,
                "amount": 2,
                "total_price": 20,
                "index": source_item.index,
            },
        )


def test_remove_outbound_order_item_cannot_remove_assigned_requirement(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.PICKING)
    product = StockProductFactory()
    source_item = OutboundOrderItemFactory(order=order, stock_product=product, amount=4)
    warehouse_order = WarehouseOrderOutFactory.it(
        order=order,
        state=OutboundWarehouseOrderState.PENDING,
    )
    assigned_item = WarehouseItemFactory.it(stock_product=product, amount=4)
    OutboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        source_order_item=source_item,
        stock_product=product,
        amount=4,
        warehouse_item=assigned_item,
    )

    with pytest.raises(
        WarehouseItemBadRequestError,
        match="Assigned warehouse items prevent removing this order item",
    ):
        client.delete(f"/{order.code}/items/{source_item.index}")


def test_update_outbound_order_rejects_changes_after_invoice(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.INVOICED)

    with pytest.raises(
        WarehouseItemBadRequestError,
        match="can no longer be edited",
    ):
        client.put(
            f"/{order.code}",
            json={
                "external_code": order.external_code,
                "description": "Updated after invoice",
                "note": order.note,
                "currency": order.currency,
                "customer_code": order.customer.code,
                "customer_name": order.customer.name,
                "requested_delivery_date": None,
            },
        )


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
    order = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)
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
    order = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)
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
    order = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)
    original_code = order.code
    product = StockProductFactory()
    OutboundOrderItemFactory(order=order, stock_product=product, amount=2)

    res = client.post(f"/{order.code}/transition", json={"action": "next"})

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["state"] == OutboundOrderState.get_label(OutboundOrderState.PICKING)
    # confirming does not renumber the order anymore (it got its final code at creation)
    assert data["code"] == original_code
    assert len(data["warehouse_orders"]) == 1
    assert data["warehouse_orders"][0]["order_code"] == data["code"]

    order.refresh_from_db()
    assert OutboundWarehouseOrder.objects.filter(order=order).count() == 1


def test_transition_outbound_order_next_skips_packing_and_shipping(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.PICKING)

    res = client.post(f"/{order.code}/transition", json={"action": "next"})

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["state"] == OutboundOrderState.get_label(OutboundOrderState.SENT)


def test_transition_outbound_order_cancel_action(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)

    res = client.post(f"/{order.code}/transition", json={"action": "cancel"})

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["state"] == OutboundOrderState.get_label(OutboundOrderState.CANCELLED)


def test_transition_outbound_order_cancel_rejects_invoiced_order(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.INVOICED)

    with pytest.raises(WarehouseItemBadRequestError, match="can no longer be edited"):
        client.post(f"/{order.code}/transition", json={"action": "cancel"})


def _codes(res) -> list[str]:
    return [o["code"] for o in res.json()["data"]]


def test_get_outbound_orders_hides_finished_orders_unless_include_all(db) -> None:
    client = TestClient(routes)
    submitted = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)
    picking = OutboundOrderFactory.it(state=OutboundOrderState.PICKING)
    for state in (
        OutboundOrderState.COMPLETED,
        OutboundOrderState.COMPLETED_PAID,
        OutboundOrderState.CANCELLED,
    ):
        OutboundOrderFactory.it(state=state)

    assert set(_codes(client.get("/"))) == {submitted.code, picking.code}
    assert len(_codes(client.get("/?include_all=true"))) == 5


def test_outbound_orders_never_list_calculations(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    OutboundCalculationFactory.it()

    assert _codes(client.get("/?include_all=true")) == [order.code]


def test_search_finds_order_by_code_of_its_calculation(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.PICKING)
    OutboundOrderFactory.it(state=OutboundOrderState.PICKING)
    OutboundCalculationFactory.it(
        code="K2026100007", order=order, state=OutboundCalculationState.CLOSED
    )

    data = client.get("/?search_term=K2026100007").json()["data"]

    assert [o["code"] for o in data] == [order.code]
    assert data[0]["calculation_code"] == "K2026100007"


def test_order_schema_has_no_calculation_code_without_calculation(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()

    data = client.get(f"/{order.code}").json()["data"]

    assert data["calculation_code"] is None
    assert "is_calculation" not in data


def test_get_outbound_orders_customer_filter_all_states_paginated(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory.it()
    for state in (
        OutboundOrderState.PICKING,
        OutboundOrderState.COMPLETED,
        OutboundOrderState.CANCELLED,
    ):
        OutboundOrderFactory.it(customer=customer, state=state)
    OutboundOrderFactory.it(state=OutboundOrderState.PICKING)  # other customer

    res = client.get(
        f"/?customer_code={customer.code}&include_all=true&page=1&page_size=2"
    )

    data = res.json()
    assert data["count"] == 3
    assert len(data["data"]) == 2
    assert data["next"] == 2


def test_cancelling_submitted_order(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it(state=OutboundOrderState.SUBMITTED)

    res = client.post(f"/{order.code}/transition", json={"action": "cancel"})

    assert res.status_code == 200
    order.refresh_from_db()
    assert order.state == OutboundOrderState.CANCELLED
    assert _codes(client.get("/?include_all=true")) == [order.code]


def test_updating_order_created_from_calculation_keeps_link(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory.it()
    order = OutboundOrderFactory.it(customer=customer, state=OutboundOrderState.PICKING)
    calculation = OutboundCalculationFactory.it(order=order, customer=customer)

    res = client.put(
        f"/{order.code}",
        json={
            "currency": "CZK",
            "customer_code": customer.code,
            "customer_name": customer.name,
            "note": "changed",
        },
    )

    assert res.status_code == 200
    assert res.json()["data"]["calculation_code"] == calculation.code
    order.refresh_from_db()
    assert order.note == "changed"


def test_duplicate_order_creates_new_submitted_order(db) -> None:
    client = TestClient(routes)
    source = OutboundOrderFactory.it(state=OutboundOrderState.PICKING)
    OutboundOrderItemFactory(order=source, stock_product=StockProductFactory())

    res = client.post(f"/{source.code}/duplicate")

    data = res.json()["data"]
    assert data["state"] == OutboundOrderState.get_label(OutboundOrderState.SUBMITTED)
    assert data["code"].startswith("OP")
    assert data["code"] != source.code
    assert data["calculation_code"] is None
    assert len(data["items"]) == 1


def _order_payload(customer, **overrides) -> dict:
    return {
        "currency": "CZK",
        "customer_code": customer.code,
        "customer_name": customer.name,
        **overrides,
    }


def test_create_outbound_order_without_contact_defaults_to_null(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()

    response = client.post("", json=_order_payload(customer))

    assert response.status_code == 200
    assert response.json()["data"]["contact"] is None
    assert OutboundOrder.objects.get().contact is None


def test_create_and_update_outbound_order_contact(db) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()
    first, second = (ContactPersonFactory.it(customer=customer) for _ in range(2))

    created = client.post("", json=_order_payload(customer, contact_id=first.id))
    assert created.status_code == 200
    data = created.json()["data"]
    assert data["contact"]["id"] == first.id

    updated = client.put(
        f"/{data['code']}", json=_order_payload(customer, contact_id=second.id)
    )
    assert updated.json()["data"]["contact"]["id"] == second.id
    assert OutboundOrder.objects.get(code=data["code"]).contact == second

    # omitting / nulling the contact clears the FK
    cleared = client.put(f"/{data['code']}", json=_order_payload(customer))
    assert cleared.json()["data"]["contact"] is None
    assert OutboundOrder.objects.get(code=data["code"]).contact is None

    got = client.get(f"/{data['code']}")
    assert got.json()["data"]["contact"] is None


@pytest.mark.parametrize("contact_kind", ["other_customer", "deleted", "missing"])
def test_outbound_order_rejects_invalid_contact(db, contact_kind: str) -> None:
    client = TestClient(routes)
    customer = CustomerFactory()
    contact_id = {
        "other_customer": lambda: ContactPersonFactory.it().id,
        "deleted": lambda: (
            ContactPersonFactory.it(customer=customer, is_deleted=True).id
        ),
        "missing": lambda: 999_999,
    }[contact_kind]()

    with pytest.raises(WarehouseItemBadRequestError, match="does not belong"):
        client.post("", json=_order_payload(customer, contact_id=contact_id))

    assert not OutboundOrder.objects.exists()


def test_update_outbound_order_rejects_contact_of_changed_customer(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    contact = ContactPersonFactory.it(customer=order.customer)
    other_customer = CustomerFactory()

    with pytest.raises(WarehouseItemBadRequestError, match="does not belong"):
        client.put(
            f"/{order.code}",
            json=_order_payload(other_customer, contact_id=contact.id),
        )


def test_duplicate_outbound_order_keeps_contact(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    contact = ContactPersonFactory.it(customer=order.customer)
    order.contact = contact
    order.save()

    response = client.post(f"/{order.code}/duplicate")

    assert response.json()["data"]["contact"]["id"] == contact.id


def _add_item(client, order, product, *, amount: float, total_price: float):
    return client.post(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": amount,
            "total_price": total_price,
            "index": 0,
        },
    )


@pytest.mark.parametrize(
    "total_price, expected_total, rounded",
    [
        (0.1, 5.0, True),
        (4.99, 5.0, True),
        (5.0, 5.0, True),
        (5.01, 5.01, False),
        (100, 100.0, False),
    ],
)
def test_add_outbound_order_item_rounds_up_to_global_minimum(
    db, total_price, expected_total, rounded
) -> None:
    GlobalSettingsFactory(minimum_item_value=5)
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    product = StockProductFactory(base_price=0.01, purchase_price=0)

    response = _add_item(client, order, product, amount=10, total_price=total_price)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_price"] == expected_total
    assert data["unit_price"] == pytest.approx(expected_total / 10)
    assert OutboundOrderItem.objects.get(order=order).total_price == Decimal(
        str(expected_total)
    )
    reason = data["pricing_details"]["reason"]
    assert ("Minimum item value 5.00 (global)" in reason) is rounded


def test_add_outbound_order_item_customer_override_beats_global(db) -> None:
    GlobalSettingsFactory(minimum_item_value=5)
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    order.customer.minimum_item_value = Decimal("20")
    order.customer.save()
    product = StockProductFactory(base_price=0.01, purchase_price=0)

    response = _add_item(client, order, product, amount=10, total_price=0.1)

    data = response.json()["data"]
    assert data["total_price"] == 20.0
    assert (
        "Minimum item value 20.00 (customer override)"
        in (data["pricing_details"]["reason"])
    )


def test_add_outbound_order_item_no_rounding_when_disabled_for_customer(db) -> None:
    GlobalSettingsFactory(minimum_item_value=5)
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    order.customer.minimum_item_value_enabled = False
    order.customer.minimum_item_value = Decimal("20")
    order.customer.save()
    product = StockProductFactory(base_price=0.01, purchase_price=0)

    response = _add_item(client, order, product, amount=10, total_price=0.1)

    data = response.json()["data"]
    assert data["total_price"] == 0.1
    assert "Minimum item value" not in data["pricing_details"]["reason"]


def test_add_outbound_order_item_no_rounding_without_any_minimum(db) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    product = StockProductFactory(base_price=0.01, purchase_price=0)

    response = _add_item(client, order, product, amount=10, total_price=0.1)

    assert response.json()["data"]["total_price"] == 0.1


def test_update_outbound_order_item_rounds_up_to_minimum(db) -> None:
    GlobalSettingsFactory(minimum_item_value=5)
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    product = StockProductFactory(base_price=0.01, purchase_price=0)
    _add_item(client, order, product, amount=10, total_price=50)

    response = client.put(
        f"/{order.code}/items/0",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 10,
            "total_price": 0.1,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_price"] == 5.0
    assert data["pricing_details"]["selected_unit_price"] == 0.5
    assert "Minimum item value 5.00 (global)" in data["pricing_details"]["reason"]


def test_get_outbound_order_explains_minimum_in_pricing_details(db) -> None:
    GlobalSettingsFactory(minimum_item_value=5)
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    product = StockProductFactory(base_price=0.01, purchase_price=0)
    OutboundOrderItemFactory(
        order=order, stock_product=product, amount=10, unit_price=0.5, total_price=5
    )

    response = client.get(f"/{order.code}")

    item = response.json()["data"]["items"][0]
    assert "Minimum item value 5.00 (global)" in item["pricing_details"]["reason"]


@pytest.mark.parametrize("removed", [0, 1, 2])
def test_remove_item_recomputes_indexes_so_next_add_succeeds(db, removed) -> None:
    client = TestClient(routes)
    order = OutboundOrderFactory.it()
    for _ in range(3):
        product = StockProductFactory()
        res = client.post(
            f"/{order.code}/items",
            json={
                "product_code": product.code,
                "product_name": product.name,
                "amount": 1,
                "total_price": 10,
            },
        )
        assert res.status_code == 200

    delete_res = client.delete(f"/{order.code}/items/{removed}")
    assert delete_res.status_code == 200
    returned = delete_res.json()["data"]
    assert returned["code"] == order.code
    assert [it["index"] for it in returned["items"]] == [0, 1]
    assert list(order.items.values_list("index", flat=True)) == [0, 1]

    product = StockProductFactory()
    res = client.post(
        f"/{order.code}/items",
        json={
            "product_code": product.code,
            "product_name": product.name,
            "amount": 1,
            "total_price": 10,
        },
    )
    assert res.status_code == 200
    assert res.json()["data"]["index"] == 2
