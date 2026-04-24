from __future__ import annotations

from typing import Any

from django.core.exceptions import FieldDoesNotExist
from django.contrib.auth.models import User
from django.db import models

from apps.warehouse.core.schemas.audit import AuditTimelineEntrySchema
from apps.warehouse.models.audit import AuditAction, AuditLog, create_audit_log
from apps.warehouse.models.warehouse import WarehouseMovement


def _get_choice_label_mapping(
    model_class: type[models.Model] | None, field_name: str
) -> dict[Any, str] | None:
    if model_class is None:
        return None

    try:
        field = model_class._meta.get_field(field_name)
    except FieldDoesNotExist:
        return None

    field_choices = getattr(field, "choices", None)
    if not field_choices:
        return None

    flat_choices = getattr(field, "flatchoices", ())
    labels: dict[Any, str] = {}
    for raw_value, label in flat_choices:
        label_text = str(label)
        labels[raw_value] = label_text
        labels[str(raw_value)] = label_text

    return labels or None


def _format_choice_value(choice_labels: dict[Any, str], value: Any) -> Any:
    if isinstance(value, list):
        return [_format_choice_value(choice_labels, item) for item in value]

    return choice_labels.get(value, choice_labels.get(str(value), value))


def _normalize_choice_changes(log: AuditLog) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_changes = log.changes if isinstance(log.changes, dict) else {}
    model_class = log.content_type.model_class()
    normalized_changes: dict[str, Any] = {}

    for field_name, value in raw_changes.items():
        choice_labels = _get_choice_label_mapping(model_class, field_name)
        if not choice_labels:
            normalized_changes[field_name] = value
            continue

        if isinstance(value, dict):
            normalized_value = dict(value)
            for key in ("old", "new", "created", "deleted"):
                if key in normalized_value:
                    normalized_value[key] = _format_choice_value(
                        choice_labels, normalized_value[key]
                    )
            normalized_changes[field_name] = normalized_value
            continue

        normalized_changes[field_name] = _format_choice_value(choice_labels, value)

    return raw_changes, normalized_changes


def _normalize_reason(
    reason: str | None, raw_changes: dict[str, Any], changes: dict[str, Any]
) -> str | None:
    if not reason:
        return reason

    normalized_reason = reason
    for field_name, raw_value in raw_changes.items():
        formatted_value = changes.get(field_name)
        if not isinstance(raw_value, dict) or not isinstance(formatted_value, dict):
            continue

        for key in ("old", "new", "created", "deleted"):
            if key not in raw_value or key not in formatted_value:
                continue

            old_text = str(raw_value[key])
            new_text = str(formatted_value[key])
            if old_text == new_text:
                continue

            normalized_reason = normalized_reason.replace(
                f"'{old_text}'", f"'{new_text}'"
            )

    return normalized_reason


def audit_log_to_timeline_entry(log: AuditLog) -> AuditTimelineEntrySchema:
    raw_changes, changes = _normalize_choice_changes(log)

    return AuditTimelineEntrySchema(
        id=log.pk,
        source="audit",
        happened_at=log.created,
        actor_user=log.user.username if log.user else None,
        action=log.action,
        reason=_normalize_reason(log.reason, raw_changes, changes),
        changes=changes,
        object_repr=log.object_repr,
    )


def movement_to_timeline_entry(movement: WarehouseMovement) -> AuditTimelineEntrySchema:
    location_from_code = (
        movement.location_from.code if movement.location_from else "None"
    )
    location_to_code = movement.location_to.code if movement.location_to else "None"
    product_code = movement.stock_product.code

    summary_parts = [
        f"Moved {movement.amount} of {product_code}",
        f"from {location_from_code}",
        f"to {location_to_code}",
    ]
    if movement.inbound_order_code:
        summary_parts.append(f"inbound order {movement.inbound_order_code.code}")
    if movement.outbound_order_code:
        summary_parts.append(f"outbound order {movement.outbound_order_code.code}")
    if movement.item_id:
        summary_parts.append(f"item #{movement.item_id}")
    if movement.batch_id:
        summary_parts.append(f"batch #{movement.batch_id}")

    summary = ", ".join(summary_parts)

    return AuditTimelineEntrySchema(
        id=movement.pk,
        source="movement",
        happened_at=movement.moved_at,
        actor_user=movement.worker.username if movement.worker else None,
        action=AuditAction.TRANSITION,
        reason=summary,
        object_repr=f"Warehouse movement #{movement.pk}",
        changes={
            "location": {"old": location_from_code, "new": location_to_code},
            "amount": str(movement.amount),
            "stock_product": movement.stock_product.name,
        },
    )


class AuditService:
    @staticmethod
    def add_entry(
        obj: models.Model,
        action: AuditAction | str,
        user: User | None | int = None,
        changes: dict | None = None,
        reason: str | None = None,
        object_repr: str | None = None,
    ) -> AuditLog:
        if isinstance(user, int):
            user = User.objects.get(pk=user)
        return create_audit_log(
            obj=obj,
            action=action,
            user=user,
            changes=changes,
            reason=reason,
            object_repr=object_repr,
        )

    @staticmethod
    def get_logs_for_object(obj: models.Model):
        return AuditLog.objects.for_object(obj).select_related("content_type", "user")  # type: ignore

    @staticmethod
    def _get_related_movements_queryset(obj: models.Model):
        queryset = WarehouseMovement.objects.select_related(
            "location_from",
            "location_to",
            "inbound_order_code",
            "outbound_order_code",
            "stock_product",
            "item",
            "batch",
            "worker",
        )

        if isinstance(obj, WarehouseMovement):
            return queryset.filter(pk=obj.pk)

        conditions = models.Q()
        for field in WarehouseMovement._meta.fields:
            if not isinstance(field, models.ForeignKey):
                continue
            if field.related_model != obj.__class__:
                continue
            conditions |= models.Q(**{field.name: obj})

        if not conditions:
            return queryset.none()

        return queryset.filter(conditions)

    @staticmethod
    def get_timeline_for_object(
        obj: models.Model,
        include_related_movements: bool = True,
    ) -> list[AuditTimelineEntrySchema]:
        logs = [
            audit_log_to_timeline_entry(log)
            for log in AuditService.get_logs_for_object(obj)
        ]

        if not include_related_movements:
            return sorted(logs, key=lambda entry: entry.happened_at, reverse=True)

        movements = [
            movement_to_timeline_entry(movement)
            for movement in AuditService._get_related_movements_queryset(obj)
        ]

        return sorted(
            logs + movements,
            key=lambda entry: entry.happened_at,
            reverse=True,
        )


audit_service = AuditService()
