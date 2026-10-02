"""Audit log entries written by the data importers"""

from collections.abc import Iterable

from django.db import models

from apps.warehouse.core.audit_messages import LocalizedAuditMessage
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction


def snapshot(obj: models.Model, fields: Iterable[str]) -> dict[str, str]:
    """Comparable text representation of the audited fields"""
    return {
        name: "" if (value := getattr(obj, name)) is None else str(value)
        for name in fields
    }


def log_import(
    obj: models.Model,
    before: dict[str, str] | None,
    after: dict[str, str],
    created_message: LocalizedAuditMessage,
    updated_message: LocalizedAuditMessage,
) -> None:
    """Log creation (all filled fields) or update (changed fields only).

    Re-importing identical data changes nothing, so no entry is written.
    """
    if before is None:
        changes = {
            name: {"old": "", "new": value} for name, value in after.items() if value
        }
        audit_service.add_entry(
            obj,
            action=AuditAction.CREATE,
            reason=created_message.CS,
            changes=changes,
        )
        return

    changes = {
        name: {"old": before[name], "new": value}
        for name, value in after.items()
        if before[name] != value
    }
    if changes:
        audit_service.add_entry(
            obj,
            action=AuditAction.UPDATE,
            reason=updated_message.CS,
            changes=changes,
        )
