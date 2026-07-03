from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.warehouse.models.manufacturing import (
    ManufacturingOrder,
    ManufacturingOrderItem,
    ManufacturingOrderState,
)
from .product import StockProductFactory


class ManufacturingOrderFactory(DjangoModelFactory):
    class Meta:
        model = ManufacturingOrder

    code = factory.Sequence(lambda n: f"PV{n:06d}")
    state = ManufacturingOrderState.IN_PROGRESS


class ManufacturingOrderItemFactory(DjangoModelFactory):
    class Meta:
        model = ManufacturingOrderItem

    order = factory.SubFactory(ManufacturingOrderFactory)
    in_product = factory.SubFactory(StockProductFactory)
    in_amount = Decimal("1")
    out_product = factory.SubFactory(StockProductFactory)
    out_amount = Decimal("1")
    index = factory.Sequence(lambda n: n)
