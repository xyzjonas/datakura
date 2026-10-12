from decimal import Decimal

from factory.django import DjangoModelFactory

from apps.warehouse.models.settings import GlobalSettings


class GlobalSettingsFactory(DjangoModelFactory):
    class Meta:
        model = GlobalSettings
        django_get_or_create = ("pk",)

    pk = 1
    minimum_item_value = Decimal("0")
