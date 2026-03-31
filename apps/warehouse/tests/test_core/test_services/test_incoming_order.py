from datetime import datetime
from typing import cast

import pytest

from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
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
    CreditNoteToSupplierItem,
    CreditNoteToSupplier,
)
from apps.warehouse.models.product import StockProduct
from apps.warehouse.tests.factories.customer import CustomerFactoryMinimal
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
    CreditNoteSupplierFactory,
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
            total_price=999,
            amount=121,
        ),
    )

    assert order.items.count() == 1
    assert order.items.first().amount == 121
    assert order.items.first().total_price == 999
    assert float(order.items.first().unit_price) == pytest.approx(999 / 121)
    assert order.items.first().stock_product.code == product.code
    assert order.items.first().stock_product.name == product.name


def test_incoming_order_add_item_duplicate_product_fails(db):
    product = cast(StockProduct, StockProductFactory())
    order = cast(InboundOrder, InboundOrderFactory())

    inbound_orders_service.add_item(
        order.code,
        InboundOrderItemCreateSchema(
            product_code=product.code,
            product_name=product.name,
            total_price=100,
            amount=2,
        ),
    )

    with pytest.raises(WarehouseItemBadRequestError):
        inbound_orders_service.add_item(
            order.code,
            InboundOrderItemCreateSchema(
                product_code=product.code,
                product_name=product.name,
                total_price=300,
                amount=5,
            ),
        )

    assert order.items.count() == 1


def test_incoming_order_update_item(db):
    order = InboundOrderFactory.it()
    item = InboundOrderItemFactory._(order=order)

    result = inbound_orders_service.update_item(
        order.code,
        InboundOrderItemCreateSchema(
            product_code=item.stock_product.code,
            product_name=item.stock_product.name,
            total_price=555,
            amount=7,
        ),
    )

    item.refresh_from_db()
    assert item.amount == 7
    assert item.total_price == 555
    assert float(item.unit_price) == pytest.approx(555 / 7)
    assert result.amount == 7
    assert result.total_price == 555
    assert float(result.unit_price) == pytest.approx(555 / 7)


def test_incoming_order_add_item_assigns_next_index(db):
    order = InboundOrderFactory.it()
    first_product = StockProductFactory.it()
    second_product = StockProductFactory.it()

    assert order.items.count() == 0

    inbound_orders_service.add_item(
        order.code,
        InboundOrderItemCreateSchema(
            product_code=first_product.code,
            product_name=first_product.name,
            total_price=100,
            amount=1,
        ),
    )

    order.refresh_from_db()
    assert order.items.count() == 1

    created = inbound_orders_service.add_item(
        order.code,
        InboundOrderItemCreateSchema(
            product_code=second_product.code,
            product_name=second_product.name,
            total_price=200,
            amount=2,
        ),
    )

    assert created.index == 1


def test_incoming_order_update_item_can_change_index(db):
    order = InboundOrderFactory.it()
    item = InboundOrderItemFactory._(order=order, index=5)

    result = inbound_orders_service.update_item(
        order.code,
        InboundOrderItemCreateSchema(
            product_code=item.stock_product.code,
            product_name=item.stock_product.name,
            total_price=555,
            amount=7,
            index=2,
        ),
    )

    item.refresh_from_db()
    assert item.index == 2
    assert result.index == 2


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


def test_create_empty_incoming(db, context):
    customer = CustomerFactoryMinimal()
    incoming_order = inbound_orders_service.update_or_create_incoming(
        InboundOrderCreateOrUpdateSchema(
            currency="CZK",
            description="foobar",
            external_code="12345",
            supplier_code=customer.code,
            supplier_name=customer.name,
        ),
        context=context,
    )
    assert incoming_order.code is not None
    assert incoming_order.description == "foobar"
    assert incoming_order.external_code == "12345"
    assert incoming_order.supplier.code == customer.code
    assert incoming_order.supplier.name == customer.name
    assert incoming_order.supplier.identification == customer.identification
    assert incoming_order.items == []


def test_edit_incoming(db, context):
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
        context=context,
    )
    assert incoming_order.code == order.code
    assert incoming_order.currency == "EUR"
    assert incoming_order.description == "foobar"
    assert incoming_order.external_code == "12345"
    assert incoming_order.supplier.code == new_customer.code
    assert incoming_order.supplier.name == new_customer.name
    assert incoming_order.supplier.identification == new_customer.identification
    assert len(incoming_order.items) == 10


def test_transition_order(db, context):
    order = InboundOrderFactory(state=InboundOrderState.DRAFT)
    assert order.state == InboundOrderState.DRAFT

    result = inbound_orders_service.transition_order(
        code=order.code,
        new_state=InboundOrderState.COMPLETED,
        context=context,
    )
    order_db = InboundOrder.objects.get(code=order.code)
    assert order_db.state == InboundOrderState.COMPLETED

    assert result == inbound_order_orm_to_schema(order_db)


def test_create_credit_note(db, context):
    order = InboundOrderFactory(state=InboundOrderState.DRAFT)

    result, created = inbound_orders_service.get_or_create_credit_note(
        order_code=order.code, context=context
    )
    assert created
    assert len(result.items) == 0


def test_create_credit_note_no_order(db, context):
    with pytest.raises(InboundOrder.DoesNotExist):
        inbound_orders_service.get_or_create_credit_note("foobar", context=context)


def test_create_credit_note_exist(db, context):
    note = CreditNoteSupplierFactory()

    result, created = inbound_orders_service.get_or_create_credit_note(
        note.order.code, context=context
    )
    assert not created
    assert CreditNoteToSupplier.objects.count() == 1
    assert len(result.items) == 0

    CreditNoteToSupplierItem.objects.create(
        stock_product=StockProductFactory(),
        amount=1.0,
        credit_note=note,
        unit_price=1.0,
    )

    result, created = inbound_orders_service.get_or_create_credit_note(
        note.order.code, context=context
    )
    assert not created
    assert CreditNoteToSupplier.objects.count() == 1
    assert len(result.items) == 1
