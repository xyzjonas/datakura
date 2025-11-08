import factory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from apps.warehouse.models.packaging import UnitOfMeasure

UOMS = {
    "KS": 1,
    "100KS": 100,
    "M": 1,
    "g": 1,
    "kg": 1000,
    "hodina": 1,
}


class UnitOfMeasureFactory(DjangoModelFactory):
    class Meta:
        model = UnitOfMeasure
        django_get_or_create = ("name",)

    name = FuzzyChoice(list(UOMS.keys()))
    amount_of_base_uom = factory.LazyAttribute(lambda o: UOMS[o.name])
    base_uom = None


def create_all_uoms():
    UnitOfMeasureFactory.create_batch(size=6)
