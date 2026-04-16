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
    InboundWarehouseOrderItem,
    InboundWarehouseOrderState,
    OutboundWarehouseOrderState,
    TrackingLevel,
)
from .order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
    OutboundOrderFactory,
)
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

    @classmethod
    def it(cls, **kwargs) -> OutboundWarehouseOrder:
        return cls(**kwargs)  # type: ignore

    code = factory.Sequence(lambda n: f"WOUT-{n:06d}")
    order = factory.SubFactory(OutboundOrderFactory)
    state = OutboundWarehouseOrderState.DRAFT


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
        """
        Creates a fully set-up warehouse order for testing.

        In DRAFT state (default): only InboundWarehouseOrderItems exist.
        In PENDING/STARTED/COMPLETED: InboundWarehouseOrderItems + WarehouseItems exist.
        """
        if not product:
            product = StockProductFactory()
        elif isinstance(product, str):
            product = StockProductFactory(code=product)

        inbound_order = InboundOrderFactory()
        pickup_location = WarehouseLocationFactory(is_putaway=not is_putaway)

        w_order = cls(
            order=inbound_order,
            pickup_location=pickup_location,
            **kwargs,
        )

        order_item = InboundWarehouseOrderItemFactory(
            warehouse_order=w_order,
            stock_product=product,
            amount=amount,
            unit_price_at_receipt=unit_price,
        )

        InboundOrderItemFactory(
            order=inbound_order,
            stock_product=product,
            amount=amount,
            unit_price=unit_price,
        )

        # Only create live WarehouseItems once the order is past DRAFT
        if w_order.state not in (
            InboundWarehouseOrderState.DRAFT,
            InboundWarehouseOrderState.IN_TRANSIT,
        ):
            WarehouseItemFactory(
                order_in=w_order,
                source_order_item=order_item,
                stock_product=product,
                amount=amount,
                location=WarehouseLocationFactory(is_putaway=is_putaway),
            )

        return w_order  # type: ignore


class InboundWarehouseOrderItemFactory(DjangoModelFactory):
    class Meta:
        model = InboundWarehouseOrderItem

    @classmethod
    def it(cls, **kwargs) -> InboundWarehouseOrderItem:
        return cls(**kwargs)  # type: ignore

    warehouse_order = factory.SubFactory(InboundWarehouseOrderFactory)
    stock_product = factory.SubFactory(StockProductFactory)
    amount = factory.Sequence(lambda n: n + 1)
    tracking_level = TrackingLevel.FUNGIBLE
    unit_price_at_receipt = 0
    index = factory.Sequence(lambda n: n)


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
    source_order_item = None
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
