from __future__ import annotations

from django.conf import settings
from django.db import models

from .base import BaseModel


class Printer(BaseModel):
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return self.code


class UserAppSettings(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="warehouse_app_settings",
    )
    default_printer = models.ForeignKey(
        Printer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_for_users",
    )

    def __str__(self) -> str:
        return f"{self.user} settings"
