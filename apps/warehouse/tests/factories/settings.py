from decimal import Decimal

from factory.django import DjangoModelFactory

from apps.warehouse.models.settings import CurrencyRate, GlobalSettings


class GlobalSettingsFactory(DjangoModelFactory):
    class Meta:
        model = GlobalSettings
        django_get_or_create = ("pk",)

    pk = 1
    minimum_item_value = Decimal("0")
    minimum_markup_percent = Decimal("0")
    base_currency = "CZK"


class CurrencyRateFactory(DjangoModelFactory):
    class Meta:
        model = CurrencyRate
        django_get_or_create = ("currency",)

    currency = "EUR"
    rate = Decimal("25")
