"""Factory Boy factories for warehouse and stock models"""

import factory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from apps.warehouse.models.product import (
    ProductType,
    ProductGroup,
    StockProduct,
)
from .units import UnitOfMeasureFactory


class ProductTypeFactory(DjangoModelFactory):
    class Meta:
        model = ProductType
        django_get_or_create = ("name",)

    name = FuzzyChoice(
        ["Raw Material", "Finished Good", "Component", "Consumable", "Tool"]
    )


class ProductGroupFactory(DjangoModelFactory):
    class Meta:
        model = ProductGroup
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Product Group {n}")
    parent = None  # Can be overridden to create hierarchies


class StockProductFactory(DjangoModelFactory):
    class Meta:
        model = StockProduct
        django_get_or_create = ("code",)

    name = factory.Sequence(lambda n: f"Product {n}")
    code = factory.Sequence(lambda n: f"PRD-{n:05d}")
    type = factory.SubFactory(ProductTypeFactory)
    group = factory.SubFactory(ProductGroupFactory)
    unit_of_measure = factory.SubFactory(UnitOfMeasureFactory)
    attributes = factory.Dict({"color": factory.Faker("color_name")})
    base_price = factory.Faker(
        "pydecimal", left_digits=4, right_digits=2, min_value=1, max_value=10000
    )
    purchase_price = factory.Faker(
        "pydecimal", left_digits=4, right_digits=2, min_value=1, max_value=10000
    )
