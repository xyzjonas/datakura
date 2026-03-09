from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .base import BaseModel


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    TRANSITION = "transition", "State Transition"
    ACCESS = "access", "Access"
    OTHER = "other", "Other"


class AuditLogQuerySet(models.QuerySet):
    def for_object(self, obj: models.Model):
        if getattr(obj, "pk", None) is None:
            return self.none()

        content_type = ContentType.objects.get_for_model(obj, for_concrete_model=False)
        return self.filter(content_type=content_type, object_id=obj.pk)


class AuditLogManager(models.Manager):
    def get_queryset(self):
        return AuditLogQuerySet(self.model, using=self._db)

    def for_object(self, obj: models.Model):
        return self.get_queryset().for_object(obj)


class AuditLog(BaseModel):
    """
    A log entry to track an action performed on a model instance.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The user who performed the action.",
    )
    action = models.CharField(
        max_length=20,
        choices=AuditAction.choices,
        db_index=True,
        help_text="The type of action performed.",
    )

    # Generic relation to the audited object
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="The model of the object being audited.",
    )
    object_id = models.PositiveIntegerField(
        db_index=True, help_text="The primary key of the object being audited."
    )
    content_object = GenericForeignKey("content_type", "object_id")

    object_repr = models.CharField(
        max_length=255,
        help_text="A human-readable representation of the object at the time of the log.",
    )

    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="A JSON diff of the changes made to the object.",
    )
    reason = models.TextField(
        blank=True, null=True, help_text="The reason or justification for the action."
    )

    objects = AuditLogManager()

    class Meta:
        ordering = ["-created"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.action.capitalize()} on {self.object_repr} by {self.user or 'System'}"


def create_audit_log(
    obj: models.Model,
    action: AuditAction | str,
    user: User | int | None = None,
    changes: dict | None = None,
    reason: str | None = None,
    object_repr: str | None = None,
) -> AuditLog:
    if getattr(obj, "pk", None) is None:
        raise ValueError("Cannot create audit log for an unsaved object")

    content_type = ContentType.objects.get_for_model(obj, for_concrete_model=False)
    normalized_action = action.value if isinstance(action, AuditAction) else action

    if isinstance(user, int):
        user = User.objects.get(pk=user)

    return AuditLog.objects.create(  # type: ignore
        user=user,
        action=normalized_action,
        content_type=content_type,
        object_id=obj.pk,
        object_repr=object_repr or str(obj),
        changes=changes or {},
        reason=reason,
    )


class AuditMixin(models.Model):
    class Meta:
        abstract = True

    def log_audit(
        self,
        action: AuditAction | str,
        user: User | None = None,
        changes: dict | None = None,
        reason: str | None = None,
        object_repr: str | None = None,
    ) -> AuditLog:
        return create_audit_log(
            self,
            action=action,
            user=user,
            changes=changes,
            reason=reason,
            object_repr=object_repr,
        )

    def get_audit_logs(self):
        return AuditLog.objects.for_object(self)
