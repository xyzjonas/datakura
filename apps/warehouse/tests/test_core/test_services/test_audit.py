from datetime import timedelta

from django.utils import timezone
import pytest

from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.services.audit import (
    audit_log_to_timeline_entry,
    audit_service,
)
from apps.warehouse.models.audit import AuditAction, AuditLog, create_audit_log
from apps.warehouse.models.orders import (
    CreditNoteState,
    InboundOrderState,
    OutboundOrderState,
)
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrderState,
    OutboundWarehouseOrderState,
)
from apps.warehouse.models.warehouse import WarehouseMovement
from apps.warehouse.tests.factories.order import (
    CreditNoteSupplierFactory,
    InboundOrderFactory,
    OutboundOrderFactory,
)
from apps.warehouse.tests.factories.user import UserFactory
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    WarehouseOrderOutFactory,
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
        reason=AuditMessages.MANUAL_CORRECTION.CS,
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
        reason=AuditMessages.INITIAL_STOCK_REGISTRATION.CS,
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


@pytest.mark.parametrize(
    (
        "factory",
        "old_state",
        "new_state",
        "reason_template",
        "expected_old",
        "expected_new",
    ),
    [
        (
            InboundOrderFactory.it,
            InboundOrderState.DRAFT,
            InboundOrderState.RECEIVING,
            AuditMessages.INBOUND_ORDER_STATE_CHANGED.CS,
            "Draft",
            "Receiving",
        ),
        (
            OutboundOrderFactory.it,
            OutboundOrderState.DRAFT,
            OutboundOrderState.PICKING,
            AuditMessages.OUTBOUND_ORDER_STATE_CHANGED.CS,
            "Draft",
            "Picking",
        ),
        (
            InboundWarehouseOrderFactory.it,
            InboundWarehouseOrderState.DRAFT,
            InboundWarehouseOrderState.PENDING,
            AuditMessages.WAREHOUSE_ORDER_STATE_CHANGED.CS,
            "Draft",
            "Pending",
        ),
        (
            WarehouseOrderOutFactory.it,
            OutboundWarehouseOrderState.DRAFT,
            OutboundWarehouseOrderState.STARTED,
            AuditMessages.WAREHOUSE_ORDER_STATE_CHANGED.CS,
            "Draft",
            "Started",
        ),
        (
            CreditNoteSupplierFactory,
            CreditNoteState.DRAFT,
            CreditNoteState.CONFIRMED,
            AuditMessages.CREDIT_NOTE_STATE_CHANGED.CS,
            "Draft",
            "Confirmed",
        ),
    ],
)
def test_timeline_formats_choice_labels_for_state_transitions(
    db,
    factory,
    old_state,
    new_state,
    reason_template,
    expected_old,
    expected_new,
):
    obj = factory(state=old_state)

    log = create_audit_log(
        obj=obj,
        action=AuditAction.TRANSITION,
        changes={"state": {"old": old_state, "new": new_state}},
        reason=reason_template.format(old_state=old_state, new_state=new_state),
    )

    entry = audit_log_to_timeline_entry(log)

    assert entry.reason == reason_template.format(
        old_state=expected_old,
        new_state=expected_new,
    )
    assert entry.changes["state"] == {"old": expected_old, "new": expected_new}
