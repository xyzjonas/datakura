from decimal import Decimal

from django.db import models

from .base import BaseModel
from .currency import CURRENCY_CHOICES


class CodeSequence(models.TextChoices):
    """How often the sequential part of generated document codes restarts"""

    MONTHLY = "monthly", "Monthly"  # OP2026110003 -> OP + YYYY + MM + 4 digits
    YEARLY = "yearly", "Yearly"  # OP202600003  -> OP + YYYY + 5 digits


# Currencies the app can do business in. Base currency is one of them, the rest can
# be used as a customer's invoicing currency (needs an exchange rate to the base one).
SUPPORTED_CURRENCIES = ["CZK", "EUR", "PLN"]
DEFAULT_BASE_CURRENCY = "CZK"


class GlobalSettings(BaseModel):
    """Application wide settings - singleton, always use `GlobalSettings.load()`"""

    # Smallest value an outbound order item may have. 0 = no minimum.
    minimum_item_value = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal("0")
    )

    # Lowest allowed profit of an outbound order / item, as přirážka (markup on top of
    # the purchase price, in %). Marže is derived from it. 0 = no guard.
    minimum_markup_percent = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0")
    )

    # Numbering schema of newly generated order codes
    code_sequence = models.CharField(
        max_length=10,
        choices=CodeSequence.choices,
        default=CodeSequence.YEARLY,
    )

    # The currency the company does its taxes in. Everything (valuation, analytics,
    # stock) is calculated in it, other currencies only exist as a label + frozen
    # amounts on outbound documents.
    base_currency = models.CharField(
        max_length=3, default=DEFAULT_BASE_CURRENCY, choices=CURRENCY_CHOICES
    )

    class Meta(BaseModel.Meta):
        verbose_name_plural = "Global settings"

    def __str__(self) -> str:
        return "Global settings"

    @classmethod
    def load(cls) -> "GlobalSettings":
        return cls.objects.get_or_create(pk=1)[0]


class CurrencyRate(BaseModel):
    """
    User defined (stable) exchange rate of a foreign currency to the base currency,
    e.g. the yearly rate issued by the central bank.

    `rate` = how many units of the base currency one unit of `currency` costs
    (EUR -> CZK: 25.00). Orders freeze the rate they were created with, so changing
    it only affects documents created later.
    """

    currency = models.CharField(max_length=3, unique=True, choices=CURRENCY_CHOICES)
    rate = models.DecimalField(max_digits=18, decimal_places=8)

    class Meta(BaseModel.Meta):
        ordering = ["currency"]

    def __str__(self) -> str:
        return f"{self.currency}: {self.rate}"
