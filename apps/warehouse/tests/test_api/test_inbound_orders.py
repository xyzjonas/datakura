from datetime import timedelta

from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.inbound_orders import routes
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.tests.factories.order import InboundOrderFactory


def test_get_inbound_order_audits(db) -> None:
    client = TestClient(routes)
    order = InboundOrderFactory.it()

    older_log = audit_service.add_entry(
        order,
        action=AuditAction.CREATE,
        reason="Order created",
    )
    newer_log = audit_service.add_entry(
        order,
        action=AuditAction.UPDATE,
        reason="Order updated",
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
