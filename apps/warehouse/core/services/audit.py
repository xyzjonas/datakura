from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models

from apps.warehouse.core.schemas.audit import AuditTimelineEntrySchema
from apps.warehouse.models.audit import AuditAction, AuditLog, create_audit_log
from apps.warehouse.models.warehouse import WarehouseMovement


def audit_log_to_timeline_entry(log: AuditLog) -> AuditTimelineEntrySchema:
    return AuditTimelineEntrySchema(
        id=log.pk,
        source="audit",
        happened_at=log.created,
        actor_user=log.user.username if log.user else None,
        action=log.action,
        reason=log.reason,
        changes=log.changes,
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
