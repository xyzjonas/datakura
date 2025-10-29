"""Factory Boy factories for warehouse and stock models"""

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from apps.warehouse.models.product import (
    UnitOfMeasure,
    ProductType,
    ProductGroup,
    StockProduct,
    UnitOfMeasureConversionFactor,
)


class UnitOfMeasureFactory(DjangoModelFactory):
    class Meta:
        model = UnitOfMeasure
        django_get_or_create = ("name",)

    name = FuzzyChoice(["Each", "Box", "Pallet", "Kilogram", "Liter", "Meter"])


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

    name = factory.Sequence(lambda n: f"Product {n}")
    code = factory.Sequence(lambda n: f"PRD-{n:05d}")
    type = factory.SubFactory(ProductTypeFactory)
    group = factory.SubFactory(ProductGroupFactory)
    base_uom = factory.SubFactory(UnitOfMeasureFactory)


class UnitOfMeasureConversionFactorFactory(DjangoModelFactory):
    class Meta:
        model = UnitOfMeasureConversionFactor

    uom = factory.SubFactory(UnitOfMeasureFactory)
    stock_product = factory.SubFactory(StockProductFactory)
    conversion_factor = factory.LazyFunction(lambda: Decimal("12.0000"))


class StockProductWithConversionsFactory(StockProductFactory):
    """Creates a StockProduct with common conversion factors"""

    @factory.post_generation
    def with_conversions(obj, create, extracted, **kwargs):
        if not create:
            return

        # Create base UoM conversion (factor = 1)
        UnitOfMeasureConversionFactorFactory(
            stock_product=obj, uom=obj.base_uom, conversion_factor=Decimal("1.0000")
        )

        # Create Box conversion (factor = 12)
        box_uom, _ = UnitOfMeasure.objects.get_or_create(name="Box")
        UnitOfMeasureConversionFactorFactory(
            stock_product=obj, uom=box_uom, conversion_factor=Decimal("12.0000")
        )

        # Create Pallet conversion (factor = 144)
        pallet_uom, _ = UnitOfMeasure.objects.get_or_create(name="Pallet")
        UnitOfMeasureConversionFactorFactory(
            stock_product=obj, uom=pallet_uom, conversion_factor=Decimal("144.0000")
        )
