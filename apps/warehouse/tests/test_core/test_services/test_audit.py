from datetime import timedelta

from django.utils import timezone

from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction, AuditLog, create_audit_log
from apps.warehouse.models.warehouse import WarehouseMovement
from apps.warehouse.tests.factories.user import UserFactory
from apps.warehouse.tests.factories.warehouse import (
    WarehouseItemFactory,
    WarehouseLocationFactory,
)


def test_create_audit_log_helper_and_queryset(db):
    item = WarehouseItemFactory()
    user = UserFactory()

    log = create_audit_log(
        obj=item,
        action=AuditAction.UPDATE,
        user=user,
        changes={"amount": {"old": "1", "new": "2"}},
        reason="Manual correction",
    )

    object_logs = AuditLog.objects.for_object(item)

    assert object_logs.count() == 1
    assert object_logs.first() == log
    assert log.content_object == item
    assert log.action == AuditAction.UPDATE


def test_timeline_includes_related_movements_and_is_ordered(db):
    item = WarehouseItemFactory(amount=2)
    user = UserFactory()
    destination = WarehouseLocationFactory(warehouse=item.location.warehouse)

    log = audit_service.add_entry(
        obj=item,
        action=AuditAction.CREATE,
        user=user,
        reason="Initial stock registration",
    )
    movement = WarehouseMovement.objects.create(
        location_from=item.location,
        location_to=destination,
        stock_product=item.stock_product,
        amount=item.amount,
        item=item,
        worker=user,
    )

    earlier = timezone.now() - timedelta(hours=1)
    later = timezone.now()
    AuditLog.objects.filter(pk=log.pk).update(created=earlier)
    WarehouseMovement.objects.filter(pk=movement.pk).update(moved_at=later)

    timeline = audit_service.get_timeline_for_object(item)

    assert len(timeline) == 2
    assert timeline[0].source == "movement"
    assert timeline[0].id == movement.pk
    assert timeline[0].action == AuditAction.TRANSITION
    assert timeline[0].object_repr == f"Warehouse movement #{movement.pk}"
    assert f"to {destination.code}" in (timeline[0].reason or "")
    assert "amount" in timeline[0].changes
    assert "stock_product" in timeline[0].changes
    assert "location" in timeline[0].changes
    assert "new" in timeline[0].changes["location"]
    assert "old" in timeline[0].changes["location"]
    assert timeline[1].source == "audit"
    assert timeline[1].id == log.pk
    assert timeline[1].action == AuditAction.CREATE
