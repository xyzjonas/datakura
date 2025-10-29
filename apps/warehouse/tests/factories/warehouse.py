"""Factory Boy factories for warehouse and stock models"""

import factory
from factory.django import DjangoModelFactory
from decimal import Decimal

from apps.warehouse.models.warehouse import (
    Warehouse,
    WarehouseLocation,
    PackageType,
    Load,
    WarehouseItem,
    WarehouseMovement,
    WarehouseOrderOut,
    WarehouseOrderIn,
)
from .product import (
    StockProductFactory,
    UnitOfMeasureFactory,
)
from .user import UserFactory


class WarehouseFactory(DjangoModelFactory):
    class Meta:
        model = Warehouse
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Warehouse {n}")
    description = factory.Faker("text", max_nb_chars=200)


class WarehouseLocationFactory(DjangoModelFactory):
    class Meta:
        model = WarehouseLocation

    code = factory.Sequence(lambda n: f"LOC-{chr(65 + (n // 100))}{n % 100:02d}")
    warehouse = factory.SubFactory(WarehouseFactory)


class PackageTypeFactory(DjangoModelFactory):
    class Meta:
        model = PackageType
        django_get_or_create = ("name",)

    name = factory.Iterator(["Box", "Pallet", "Crate", "Bundle", "Bag"])
    description = factory.Faker("text", max_nb_chars=100)
    count = factory.Faker("random_int", min=1, max=100)


class LoadFactory(DjangoModelFactory):
    class Meta:
        model = Load

    code = factory.Sequence(lambda n: f"LOAD-{n:06d}")
    current_location = factory.SubFactory(WarehouseLocationFactory)
    status = factory.Iterator(["In_Use", "Empty", "Inspection", "Quarantine"])


class WarehouseItemFactory(DjangoModelFactory):
    class Meta:
        model = WarehouseItem

    code = factory.Sequence(lambda n: f"ITEM-{n:08d}")
    stock_item = factory.SubFactory(StockProductFactory)
    uom_at_receipt = factory.SubFactory(UnitOfMeasureFactory)
    conversion_factor_at_receipt = factory.LazyFunction(lambda: Decimal("12.0000"))
    warehouse_location = factory.SubFactory(WarehouseLocationFactory)
    remaining = factory.LazyAttribute(
        lambda obj: obj.conversion_factor_at_receipt
    )  # Start with full quantity


class WarehouseMovementFactory(DjangoModelFactory):
    class Meta:
        model = WarehouseMovement

    location_from = factory.SubFactory(WarehouseLocationFactory)
    location_to = factory.SubFactory(WarehouseLocationFactory)
    worker = factory.SubFactory(UserFactory)

    # By default, create a Load movement
    load = factory.SubFactory(LoadFactory)
    item = None

    class Params:
        # Use this trait to create an item movement instead
        item_movement = factory.Trait(
            load=None,
            item=factory.SubFactory(WarehouseItemFactory),
        )


class WarehouseOrderOutFactory(DjangoModelFactory):
    class Meta:
        model = WarehouseOrderOut

    # Add fields as they are defined in your model
    pass


class WarehouseOrderInFactory(DjangoModelFactory):
    class Meta:
        model = WarehouseOrderIn

    # Add fields as they are defined in your model
    pass


class WarehouseWithLocationsFactory(WarehouseFactory):
    """Creates a Warehouse with multiple locations"""

    @factory.post_generation
    def with_locations(obj, create, extracted, **kwargs):
        if not create:
            return

        num_locations = extracted or 5
        for i in range(num_locations):
            WarehouseLocationFactory(
                warehouse=obj, code=f"{obj.name}-{chr(65 + i)}{i:02d}"
            )
