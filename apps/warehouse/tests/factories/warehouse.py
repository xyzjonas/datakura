"""Factory Boy factories for warehouse and stock models"""

import factory
from factory.django import DjangoModelFactory

from apps.warehouse.models.warehouse import (
    Warehouse,
    WarehouseLocation,
    WarehouseItem,
    WarehouseMovement,
    OutboundWarehouseOrder,
    InboundWarehouseOrder,
    InboundWarehouseOrderState,
)
from .order import InboundOrderFactory
from .product import (
    StockProductFactory,
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
    is_putaway = False


class WarehouseItemFactory(DjangoModelFactory):
    class Meta:
        model = WarehouseItem

    code = factory.Sequence(lambda n: f"ITEM-{n:08d}")
    stock_product = factory.SubFactory(StockProductFactory)
    package_type = None
    location = factory.SubFactory(WarehouseLocationFactory)
    amount = 0
    order_in = None


class WarehouseMovementFactory(DjangoModelFactory):
    class Meta:
        model = WarehouseMovement

    location_from = factory.SubFactory(WarehouseLocationFactory)
    location_to = factory.SubFactory(WarehouseLocationFactory)
    worker = factory.SubFactory(UserFactory)

    item = None

    class Params:
        # Use this trait to create an item movement instead
        item_movement = factory.Trait(
            load=None,
            item=factory.SubFactory(WarehouseItemFactory),
        )


class WarehouseOrderOutFactory(DjangoModelFactory):
    class Meta:
        model = OutboundWarehouseOrder

    # Add fields as they are defined in your model
    pass


class WarehouseOrderInFactory(DjangoModelFactory):
    class Meta:
        model = InboundWarehouseOrder

    # Add fields as they are defined in your model
    code = factory.Sequence(lambda n: f"ORD-{n:06d}")
    order = factory.SubFactory(InboundOrderFactory)
    state = InboundWarehouseOrderState.DRAFT


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
