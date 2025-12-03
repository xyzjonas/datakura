from datetime import datetime
from typing import cast

from apps.warehouse.core.schemas.orders import (
    InboundOrderItemCreateSchema,
    InboundOrderCreateOrUpdateSchema,
)
from apps.warehouse.core.services.orders import inbound_orders_service
from apps.warehouse.core.transformation import inbound_order_orm_to_schema
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderItem,
    InboundOrderState,
)
from apps.warehouse.models.product import StockProduct
from apps.warehouse.tests.factories.customer import CustomerFactoryMinimal
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory


def test_incoming_order_add_item(db):
    product = cast(StockProduct, StockProductFactory())
    order = cast(InboundOrder, InboundOrderFactory())

    inbound_orders_service.add_item(
        order.code,
        InboundOrderItemCreateSchema(
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
    order = cast(InboundOrder, InboundOrderFactory())
    items = InboundOrderItemFactory.create_batch(10, order=order)

    item = cast(InboundOrderItem, items[0])

    assert inbound_orders_service.remove_item(order.code, item.stock_product.code)

    assert order.items.count() == 9


def test_incoming_order_remove_2_items_same_product(db):
    order = cast(InboundOrder, InboundOrderFactory())
    product = cast(StockProduct, StockProductFactory())
    InboundOrderItemFactory.create_batch(2, order=order, stock_product=product)

    assert order.items.count() == 2

    assert inbound_orders_service.remove_item(order.code, product.code)

    assert order.items.count() == 0


def test_generate_next_incoming_order_code(db):
    now = datetime.now()
    code = inbound_orders_service.generate_next_incoming_order_code()
    assert code == f"OV{now.year}{now.month:02d}0001"


def test_generate_next_incoming_order_code_100(db):
    InboundOrderFactory.create_batch(99)
    now = datetime.now()
    code = inbound_orders_service.generate_next_incoming_order_code()
    assert code == f"OV{now.year}{now.month:02d}0100"


def test_create_empty_incoming(db):
    customer = CustomerFactoryMinimal()
    incoming_order = inbound_orders_service.update_or_create_incoming(
        InboundOrderCreateOrUpdateSchema(
            currency="CZK",
            description="foobar",
            external_code="12345",
            supplier_code=customer.code,
            supplier_name=customer.name,
        )
    )
    assert incoming_order.code is not None
    assert incoming_order.description == "foobar"
    assert incoming_order.external_code == "12345"
    assert incoming_order.supplier.code == customer.code
    assert incoming_order.supplier.name == customer.name
    assert incoming_order.supplier.identification == customer.identification
    assert incoming_order.items == []


def test_edit_incoming(db):
    order = InboundOrderFactory(currency="CZK")
    InboundOrderItemFactory.create_batch(10, order=order)

    new_customer = CustomerFactoryMinimal()
    incoming_order = inbound_orders_service.update_or_create_incoming(
        InboundOrderCreateOrUpdateSchema(
            currency="EUR",
            description="foobar",
            external_code="12345",
            supplier_code=new_customer.code,
            supplier_name=new_customer.name,
        ),
        code=order.code,
    )
    assert incoming_order.code == order.code
    assert incoming_order.currency == "EUR"
    assert incoming_order.description == "foobar"
    assert incoming_order.external_code == "12345"
    assert incoming_order.supplier.code == new_customer.code
    assert incoming_order.supplier.name == new_customer.name
    assert incoming_order.supplier.identification == new_customer.identification
    assert len(incoming_order.items) == 10


def test_transition_order(db):
    order = InboundOrderFactory(state=InboundOrderState.DRAFT)
    assert order.state == InboundOrderState.DRAFT

    result = inbound_orders_service.transition_order(
        order.code, InboundOrderState.COMPLETED
    )
    order_db = InboundOrder.objects.get(code=order.code)
    assert order_db.state == InboundOrderState.COMPLETED

    assert result == inbound_order_orm_to_schema(order_db)
