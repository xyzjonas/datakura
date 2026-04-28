from datetime import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.warehouse.core.exceptions import (
    WarehouseItemBadRequestError,
    WarehouseOrderNotEditableError,
)
from apps.warehouse.core.schemas.invoice import InvoiceStoreSchema
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
from apps.warehouse.tests.factories.customer import CustomerFactoryMinimal
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
    CreditNoteSupplierFactory,
    InvoiceFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import InboundWarehouseOrderFactory


def test_incoming_order_add_item(db):
    product = StockProductFactory.it()
    order = InboundOrderFactory.it()

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
    created_item = order.items.first()
    assert created_item is not None
    assert created_item.amount == 121
    assert created_item.total_price == 999
    assert float(created_item.unit_price) == pytest.approx(999 / 121)
    assert created_item.stock_product.code == product.code
    assert created_item.stock_product.name == product.name


def test_incoming_order_add_item_duplicate_product_fails(db):
    product = StockProductFactory.it()
    order = InboundOrderFactory.it()

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
    item = InboundOrderItemFactory.it(order=order)

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
    item = InboundOrderItemFactory.it(order=order, index=5)

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
    order = InboundOrderFactory.it()
    item = InboundOrderItemFactory.it(order=order)
    InboundOrderItemFactory.create_batch(9, order=order)

    assert inbound_orders_service.remove_item(order.code, item.stock_product.code)

    assert order.items.count() == 9


def test_incoming_order_remove_2_items_same_product(db):
    order = InboundOrderFactory.it()
    product = StockProductFactory.it()
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
    customer = CustomerFactoryMinimal.it()
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

    new_customer = CustomerFactoryMinimal.it()
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


def test_edit_submitted_incoming_without_warehouse_order(db, context):
    order = InboundOrderFactory(
        currency="CZK",
        state=InboundOrderState.SUBMITTED,
    )

    new_customer = CustomerFactoryMinimal.it()
    incoming_order = inbound_orders_service.update_or_create_incoming(
        InboundOrderCreateOrUpdateSchema(
            currency="EUR",
            description="still editable",
            external_code="12345",
            supplier_code=new_customer.code,
            supplier_name=new_customer.name,
        ),
        code=order.code,
        context=context,
    )

    assert incoming_order.code == order.code
    assert incoming_order.currency == "EUR"
    assert incoming_order.description == "still editable"


@pytest.mark.parametrize(
    ("operation", "needs_existing_item"),
    [
        ("update_order", False),
        ("add_item", False),
        ("update_item", True),
        ("remove_item", True),
        ("store_invoice", False),
    ],
)
def test_incoming_order_mutations_blocked_after_warehouse_order_created(
    db,
    context,
    operation: str,
    needs_existing_item: bool,
):
    order = InboundOrderFactory.it(state=InboundOrderState.SUBMITTED)
    existing_item: InboundOrderItem | None = None
    if needs_existing_item:
        existing_item = InboundOrderItemFactory.it(order=order)
    InboundWarehouseOrderFactory(order=order)
    product = StockProductFactory.it()
    CustomerFactoryMinimal.it(is_self=True)

    with pytest.raises(WarehouseOrderNotEditableError, match="read only"):
        if operation == "update_order":
            replacement_supplier = CustomerFactoryMinimal.it()
            inbound_orders_service.update_or_create_incoming(
                InboundOrderCreateOrUpdateSchema(
                    currency="EUR",
                    description="blocked",
                    external_code="12345",
                    supplier_code=replacement_supplier.code,
                    supplier_name=replacement_supplier.name,
                ),
                code=order.code,
                context=context,
            )
        elif operation == "add_item":
            inbound_orders_service.add_item(
                order.code,
                InboundOrderItemCreateSchema(
                    product_code=product.code,
                    product_name=product.name,
                    total_price=100,
                    amount=2,
                ),
            )
        elif operation == "update_item":
            assert existing_item is not None
            inbound_orders_service.update_item(
                order.code,
                InboundOrderItemCreateSchema(
                    product_code=existing_item.stock_product.code,
                    product_name=existing_item.stock_product.name,
                    total_price=555,
                    amount=7,
                ),
            )
        elif operation == "remove_item":
            assert existing_item is not None
            inbound_orders_service.remove_item(
                order.code, existing_item.stock_product.code
            )
        elif operation == "store_invoice":
            inbound_orders_service.store_invoice(
                order.code,
                InvoiceStoreSchema(
                    customer_code=None,
                    supplier_code=order.supplier.code,
                    code="INV-BLOCKED-0001",
                    issued_date=datetime(2026, 3, 10).date(),
                    due_date=datetime(2026, 3, 31).date(),
                    payment_method_name="Bank transfer",
                    external_code="SUP-INV-001",
                    taxable_supply_date=datetime(2026, 3, 10).date(),
                    paid_date=None,
                    currency="CZK",
                    note="Blocked invoice",
                ),
                context=context,
                invoice_file=SimpleUploadedFile(
                    "invoice.pdf",
                    b"%PDF-1.4 blocked invoice",
                    content_type="application/pdf",
                ),
            )
        else:
            raise AssertionError(f"Unexpected operation: {operation}")


def test_transition_order(db, context):
    order = InboundOrderFactory(state=InboundOrderState.DRAFT)
    assert order.state == InboundOrderState.DRAFT

    result = inbound_orders_service.transition_order(
        code=order.code,
        context=context,
        target_state=InboundOrderState.COMPLETED,
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


def test_store_invoice_creates_and_attaches_to_inbound_order(
    db, context, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"

    order = InboundOrderFactory()
    customer = CustomerFactoryMinimal.it(is_self=True)
    supplier = CustomerFactoryMinimal.it()

    result = inbound_orders_service.store_invoice(
        order.code,
        InvoiceStoreSchema(
            customer_code=customer.code,
            supplier_code=supplier.code,
            code="INV-STORE-0001",
            issued_date=datetime(2026, 3, 10).date(),
            due_date=datetime(2026, 3, 31).date(),
            payment_method_name="Bank transfer",
            external_code="SUP-INV-001",
            taxable_supply_date=datetime(2026, 3, 10).date(),
            paid_date=None,
            currency="CZK",
            note="March invoice",
        ),
        context=context,
        invoice_file=SimpleUploadedFile(
            "invoice.pdf",
            b"%PDF-1.4 test invoice",
            content_type="application/pdf",
        ),
    )

    order.refresh_from_db()

    assert order.invoice is not None
    assert order.invoice.code == "INV-STORE-0001"
    assert order.invoice.customer == customer
    assert order.invoice.supplier == supplier
    assert order.invoice.payment_method.name == "Bank transfer"
    assert order.invoice.document.name.endswith("invoice.pdf")
    assert result.invoice is not None
    assert result.invoice.document is not None
    assert result.invoice.document.name == "invoice.pdf"
    assert result.invoice.document.url.endswith("invoice.pdf")


def test_store_invoice_updates_existing_invoice(db, context, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"

    self_customer = CustomerFactoryMinimal.it(is_self=True)
    invoice = InvoiceFactory.it(code="INV-EXISTING-0001")
    order = InboundOrderFactory.it(invoice=invoice)

    result = inbound_orders_service.store_invoice(
        order.code,
        InvoiceStoreSchema(
            customer_code=None,
            supplier_code=None,
            code="INV-EXISTING-0001",
            issued_date=datetime(2026, 4, 1).date(),
            due_date=datetime(2026, 4, 15).date(),
            payment_method_name="Cash",
            external_code="UPDATED-EXT-001",
            taxable_supply_date=datetime(2026, 4, 1).date(),
            paid_date=datetime(2026, 4, 3).date(),
            currency="EUR",
            note="Updated invoice",
        ),
        context=context,
    )

    order.refresh_from_db()
    invoice.refresh_from_db()

    assert order.invoice == invoice
    assert invoice.customer == self_customer
    assert invoice.supplier is None
    assert invoice.payment_method.name == "Cash"
    assert invoice.external_code == "UPDATED-EXT-001"
    assert invoice.currency == "EUR"
    assert result.invoice is not None
    assert result.invoice.payment_method.name == "Cash"


def test_store_invoice_ignores_provided_customer_and_uses_self_customer(
    db, context, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"

    order = InboundOrderFactory()
    self_customer = CustomerFactoryMinimal.it(is_self=True)
    provided_customer = CustomerFactoryMinimal.it()
    supplier = CustomerFactoryMinimal.it()

    inbound_orders_service.store_invoice(
        order.code,
        InvoiceStoreSchema(
            customer_code=provided_customer.code,
            supplier_code=supplier.code,
            code="INV-STORE-0002",
            issued_date=datetime(2026, 3, 10).date(),
            due_date=datetime(2026, 3, 31).date(),
            payment_method_name="Bank transfer",
            external_code=None,
            taxable_supply_date=datetime(2026, 3, 10).date(),
            paid_date=None,
            currency="CZK",
            note=None,
        ),
        context=context,
    )

    order.refresh_from_db()
    assert order.invoice is not None
    assert order.invoice.customer == self_customer
