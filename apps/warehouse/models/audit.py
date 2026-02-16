from django.conf import settings
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

    class Meta:
        ordering = ["-created"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.action.capitalize()} on {self.object_repr} by {self.user or 'System'}"
