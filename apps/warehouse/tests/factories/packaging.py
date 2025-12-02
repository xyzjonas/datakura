import factory
from factory.django import DjangoModelFactory

from apps.warehouse.models.packaging import PackageType
from .units import UnitOfMeasureFactory

PTYPES = {
    "B0100": 100,
    "B0200": 200,
    "B0400": 200,
    "B1000": 1000,
}


class PackageTypeFactory(DjangoModelFactory):
    class Meta:
        model = PackageType
        django_get_or_create = ("name",)

    name = factory.Iterator(PTYPES.keys())
    description = None
    amount = factory.LazyAttribute(lambda o: PTYPES[o.name])
    unit_of_measure = factory.SubFactory(UnitOfMeasureFactory)


def create_all_package_types():
    PackageTypeFactory.create_batch(size=4)
