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
from .order import InboundOrderFactory, InboundOrderItemFactory
from .product import (
    StockProductFactory,
)
from .user import UserFactory
from ...models.product import StockProduct


class WarehouseFactory(DjangoModelFactory):
    class Meta:
        model = Warehouse
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Warehouse {n}")
    description = factory.Faker("text", max_nb_chars=200)


class WarehouseLocationFactory(DjangoModelFactory):
    class Meta:
        model = WarehouseLocation

    @classmethod
    def it(cls, **kwargs) -> WarehouseLocation:
        return cls(**kwargs)  # type: ignore

    code = factory.Sequence(lambda n: f"LOC-{chr(65 + (n // 100))}{n % 100:02d}")
    warehouse = factory.SubFactory(WarehouseFactory)
    is_putaway = False


class WarehouseOrderOutFactory(DjangoModelFactory):
    class Meta:
        model = OutboundWarehouseOrder

    # Add fields as they are defined in your model
    pass


class InboundWarehouseOrderFactory(DjangoModelFactory):
    class Meta:
        model = InboundWarehouseOrder

    # Add fields as they are defined in your model
    code = factory.Sequence(lambda n: f"ORD-{n:06d}")
    order = factory.SubFactory(InboundOrderFactory)
    state = InboundWarehouseOrderState.DRAFT

    @classmethod
    def it(cls, **kwargs) -> InboundWarehouseOrder:
        return cls(**kwargs)  # type: ignore

    @classmethod
    def create_complete(
        cls,
        product: StockProduct | StockProductFactory | str | None = None,
        amount: float = 100,
        unit_price: float = 1,
        is_putaway: bool = False,
        **kwargs,
    ) -> InboundWarehouseOrder:
        if not product:
            product = StockProductFactory()
        elif isinstance(product, str):
            product = StockProductFactory(code=product)

        inbound_order = InboundOrderFactory()

        w_order = cls(order=inbound_order, **kwargs)
        w_order.order = inbound_order  # type: ignore

        WarehouseItemFactory(
            order_in=w_order,
            stock_product=product,
            amount=amount,
            location=WarehouseLocationFactory(is_putaway=is_putaway),
        )

        InboundOrderItemFactory(
            order=inbound_order,
            stock_product=product,
            amount=amount,
            unit_price=unit_price,
        )

        return w_order  # type: ignore


class WarehouseItemFactory(DjangoModelFactory):
    class Meta:
        model = WarehouseItem

    @classmethod
    def it(cls, **kwargs) -> WarehouseItem:
        return cls(**kwargs)  # type: ignore

    stock_product = factory.SubFactory(StockProductFactory)
    package_type = None
    location = factory.SubFactory(WarehouseLocationFactory)
    order_in = factory.SubFactory(InboundWarehouseOrderFactory)
    tracking_level = "FUNGIBLE"
    amount = 0


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
