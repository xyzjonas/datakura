"""
Exchange rates of foreign currencies to the base currency.

`ExchangeRateProvider` is the seam to plug in another source (e.g. real-time rates):
implement it and point `settings.EXCHANGE_RATE_PROVIDER` (dotted path) to the class.
The default `ManualExchangeRateProvider` serves the stable, user defined rates from
the app settings (e.g. the yearly rate issued by the central bank).

Rates are only ever *read* when a document gets its currency; the rate is then frozen
on the document, so a provider switch or a rate change never touches existing ones.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from django.conf import settings
from django.utils.module_loading import import_string

from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.models.settings import CurrencyRate

RATE_QUANTUM = Decimal("0.00000001")


class ExchangeRateProvider(Protocol):
    def get_rate(self, currency: str, base_currency: str) -> Decimal | None:
        """Base currency units per 1 unit of `currency`, None if not available."""
        ...


class ManualExchangeRateProvider:
    """User defined rates stored in `CurrencyRate`."""

    def get_rate(self, currency: str, base_currency: str) -> Decimal | None:
        rate = CurrencyRate.objects.filter(currency=currency).first()
        return Decimal(str(rate.rate)) if rate else None


def get_provider() -> ExchangeRateProvider:
    path = getattr(
        settings,
        "EXCHANGE_RATE_PROVIDER",
        "apps.warehouse.core.services.exchange_rates.ManualExchangeRateProvider",
    )
    return import_string(path)()


class ExchangeRatesService:
    @staticmethod
    def get_rate(currency: str, base_currency: str) -> Decimal:
        """Rate to freeze on a document; 1 for the base currency itself."""
        if currency == base_currency:
            return Decimal("1")
        rate = get_provider().get_rate(currency, base_currency)
        if rate is None or rate <= 0:
            raise WarehouseItemBadRequestError(
                f"No exchange rate {currency} -> {base_currency} is set up."
            )
        return rate

    @staticmethod
    def to_base(amount: Decimal, rate: Decimal) -> Decimal:
        return (amount * rate).quantize(Decimal("0.0001"))

    @staticmethod
    def from_base(amount: Decimal, rate: Decimal) -> Decimal:
        return (amount / rate).quantize(Decimal("0.0001"))


exchange_rates_service = ExchangeRatesService()
