from decimal import Decimal

from django.db import models

from .base import BaseModel


class CodeSequence(models.TextChoices):
    """How often the sequential part of generated document codes restarts"""

    MONTHLY = "monthly", "Monthly"  # OP2026110003 -> OP + YYYY + MM + 4 digits
    YEARLY = "yearly", "Yearly"  # OP202600003  -> OP + YYYY + 5 digits


class GlobalSettings(BaseModel):
    """Application wide settings - singleton, always use `GlobalSettings.load()`"""

    # Smallest value an outbound order item may have. 0 = no minimum.
    minimum_item_value = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal("0")
    )

    # Numbering schema of newly generated order codes
    code_sequence = models.CharField(
        max_length=10,
        choices=CodeSequence.choices,
        default=CodeSequence.YEARLY,
    )

    class Meta(BaseModel.Meta):
        verbose_name_plural = "Global settings"

    def __str__(self) -> str:
        return "Global settings"

    @classmethod
    def load(cls) -> "GlobalSettings":
        return cls.objects.get_or_create(pk=1)[0]
