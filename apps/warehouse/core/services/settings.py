from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from django.db import transaction

from apps.warehouse.core.schemas.settings import GlobalSettingsUpdateSchema
from apps.warehouse.models.customer import Customer
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.models.settings import (
    SUPPORTED_CURRENCIES,
    CurrencyRate,
    GlobalSettings,
)


class MinimumItemValueSource(StrEnum):
    GLOBAL = "global"
    CUSTOMER = "customer"


@dataclass(frozen=True)
class MinimumItemValue:
    value: Decimal
    source: MinimumItemValueSource

    @property
    def explanation(self) -> str:
        origin = (
            "customer override"
            if self.source == MinimumItemValueSource.CUSTOMER
            else "global"
        )
        return f"Minimum item value {self.value.quantize(Decimal('0.01'))} ({origin})"


class SettingsService:
    @staticmethod
    def get_settings() -> GlobalSettings:
        return GlobalSettings.load()

    @staticmethod
    @transaction.atomic
    def update_settings(params: GlobalSettingsUpdateSchema) -> GlobalSettings:
        settings = GlobalSettings.load()
        if params.minimum_item_value is not None:
            settings.minimum_item_value = Decimal(str(params.minimum_item_value))
        if params.minimum_markup_percent is not None:
            settings.minimum_markup_percent = Decimal(
                str(params.minimum_markup_percent)
            )
        if params.code_sequence is not None:
            settings.code_sequence = params.code_sequence
        if (
            params.base_currency is not None
            and params.base_currency != settings.base_currency
        ):
            SettingsService.assert_supported_currency(params.base_currency)
            settings.base_currency = params.base_currency
            # rates are relative to the base currency - the old ones are meaningless
            CurrencyRate.objects.all().delete()
        settings.save()
        for rate in params.exchange_rates or []:
            SettingsService.assert_supported_currency(rate.currency)
            if rate.currency == settings.base_currency:
                raise WarehouseItemBadRequestError(
                    "Base currency has no exchange rate (it is always 1)."
                )
            CurrencyRate.objects.update_or_create(
                currency=rate.currency, defaults={"rate": Decimal(str(rate.rate))}
            )
        return settings

    @staticmethod
    def assert_supported_currency(currency: str) -> None:
        if currency not in SUPPORTED_CURRENCIES:
            raise WarehouseItemBadRequestError(
                f"Currency '{currency}' is not supported "
                f"(supported: {', '.join(SUPPORTED_CURRENCIES)})."
            )

    @staticmethod
    def get_base_currency() -> str:
        return GlobalSettings.load().base_currency

    @staticmethod
    def resolve_document_currency(
        customer: Customer | None, requested: str | None = None
    ) -> str:
        """Explicit choice > the customer's currency override > the base currency."""
        if requested:
            SettingsService.assert_supported_currency(requested)
            return requested
        if customer is not None and customer.currency:
            return customer.currency
        return SettingsService.get_base_currency()

    @staticmethod
    def resolve_minimum_item_value(
        customer: Customer | None,
    ) -> MinimumItemValue | None:
        """
        Minimum value of a single order item for the customer, or None if no minimum
        applies (turned off for the customer / no positive minimum configured).
        """
        if customer is not None:
            if not customer.minimum_item_value_enabled:
                return None
            if customer.minimum_item_value is not None:
                minimum = Decimal(str(customer.minimum_item_value))
                source = MinimumItemValueSource.CUSTOMER
                return MinimumItemValue(minimum, source) if minimum > 0 else None

        minimum = Decimal(str(GlobalSettings.load().minimum_item_value))
        if minimum <= 0:
            return None
        return MinimumItemValue(minimum, MinimumItemValueSource.GLOBAL)

    @staticmethod
    def apply_minimum_item_value(
        customer: Customer | None, total_price: Decimal
    ) -> Decimal:
        """Round the item total up to the minimum item value (if any applies)"""
        minimum = SettingsService.resolve_minimum_item_value(customer)
        if minimum is None:
            return total_price
        return max(total_price, minimum.value)


settings_service = SettingsService()
