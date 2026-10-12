from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from django.db import transaction

from apps.warehouse.core.schemas.settings import GlobalSettingsUpdateSchema
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.settings import GlobalSettings


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
        settings.minimum_item_value = Decimal(str(params.minimum_item_value))
        settings.save()
        return settings

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
