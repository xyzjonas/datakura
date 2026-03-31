from datetime import timedelta

from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.inbound_orders import routes
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.tests.factories.order import InboundOrderFactory
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
