from typing import cast

from apps.warehouse.core.schemas.orders import IncomingOrderItemCreateSchema
from apps.warehouse.core.services.orders import incoming_orders_service
from apps.warehouse.models.orders import IncomingOrder, IncomingOrderItem
from apps.warehouse.models.product import StockProduct
from apps.warehouse.tests.factories.order import (
    IncomingOrderFactory,
    IncomingOrderItemFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory


def test_incoming_order_add_item(db):
    product = cast(StockProduct, StockProductFactory())
    order = cast(IncomingOrder, IncomingOrderFactory())

    incoming_orders_service.add_item(
        order.code,
        IncomingOrderItemCreateSchema(
            product_code=product.code,
            product_name=product.name,
            unit_price=999,
            amount=121,
        ),
    )

    assert order.items.count() == 1
    assert order.items.first().amount == 121
    assert order.items.first().unit_price == 999
    assert order.items.first().stock_product.code == product.code
    assert order.items.first().stock_product.name == product.name


def test_incoming_order_remove_item(db):
    order = cast(IncomingOrder, IncomingOrderFactory())
    items = IncomingOrderItemFactory.create_batch(10, order=order)

    item = cast(IncomingOrderItem, items[0])

    assert incoming_orders_service.remove_item(order.code, item.stock_product.code)

    assert order.items.count() == 9


def test_incoming_order_remove_2_items_same_product(db):
    order = cast(IncomingOrder, IncomingOrderFactory())
    product = cast(StockProduct, StockProductFactory())
    IncomingOrderItemFactory.create_batch(2, order=order, stock_product=product)

    assert order.items.count() == 2

    assert incoming_orders_service.remove_item(order.code, product.code)

    assert order.items.count() == 0
