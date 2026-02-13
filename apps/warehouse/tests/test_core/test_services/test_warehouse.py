from typing import cast

import pytest
from django.utils import timezone

from apps.warehouse.core.exceptions import WarehouseItemGenericError
from apps.warehouse.core.schemas.warehouse import (
    WarehouseOrderCreateSchema,
    WarehouseItemSchema,
)
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.core.transformation import (
    product_orm_to_schema,
    location_orm_to_schema,
    package_orm_to_schema,
    warehouse_item_orm_to_schema,
)
from apps.warehouse.models.orders import CreditNoteState
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    WarehouseLocation,
    WarehouseItem,
    InboundWarehouseOrder,
    InboundWarehouseOrderState,
)
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
)
from apps.warehouse.tests.factories.packaging import PackageTypeFactory
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.units import UnitOfMeasureFactory
from apps.warehouse.tests.factories.warehouse import (
    WarehouseItemFactory,
    InboundWarehouseOrderFactory,
    CompleteOrderFactory,
)
from apps.warehouse.tests.factories.warehouse import WarehouseLocationFactory


@pytest.fixture
def putaway(db) -> WarehouseLocation:
    return cast(WarehouseLocation, WarehouseLocationFactory(is_putaway=True))


def test_create_warehouse_inbound_order(putaway):
    order = InboundOrderFactory()
    InboundOrderItemFactory.create_batch(10, order=order)

    result = warehouse_service.create_inbound_order(
        WarehouseOrderCreateSchema(
            purchase_order_code=order.code, location_code=putaway.code
        )
    )

    assert len(result.items) == 10


@pytest.mark.parametrize("items_amount, amount", [(3, 99), (0, 10), (3, 1.2)])
def test_get_warehouse_availability(db, items_amount, amount):
    product = cast(StockProduct, StockProductFactory())
    WarehouseItemFactory.create_batch(
        items_amount, amount=amount, stock_product=product
    )
    assert warehouse_service.get_warehouse_availability(product.code) == pytest.approx(
        items_amount * amount
    )


@pytest.mark.parametrize("items_amount, amount", [(10, 10), (0, 10), (3, 1.2)])
def test_get_total_availability(db, items_amount, amount):
    product = cast(StockProduct, StockProductFactory())
    WarehouseItemFactory.create_batch(
        items_amount, amount=amount, stock_product=product
    )
    result = warehouse_service.get_total_availability(product.code)
    assert result.total_amount == pytest.approx(items_amount * amount)
    assert result.available_amount == pytest.approx(items_amount * amount)


def test_update_inbound_order_items(db):
    order = InboundWarehouseOrderFactory()
    pkg = PackageTypeFactory()
    new_location = WarehouseLocationFactory()
    old_item = WarehouseItemFactory(order_in=order, amount=10)

    count = 10
    new_items = [
        WarehouseItemSchema(
            id=-1,
            code="...",
            unit_of_measure=old_item.stock_product.unit_of_measure.name,
            created=timezone.now(),
            changed=timezone.now(),
            product=product_orm_to_schema(old_item.stock_product),
            location=location_orm_to_schema(new_location),
            amount=1,
            package=package_orm_to_schema(pkg),
        )
        for _ in range(count)
    ]
    to_be_deleted = [warehouse_item_orm_to_schema(old_item)]

    result = warehouse_service.add_or_remove_inbound_order_items(
        order.code, to_be_deleted, new_items
    )
    assert WarehouseItem.objects.filter(code=old_item.code).first() is None
    assert result.code == order.code
    assert result.state == order.state
    assert len(result.items) == count
    for item in result.items:
        assert item.location.code == new_location.code
        assert item.code != old_item.code
        assert item.package.type == pkg.name
        assert item.product.code == old_item.stock_product.code


def test_setup_tracking_for_inbound_order_item_total(db):
    order = InboundWarehouseOrderFactory()
    pkg = PackageTypeFactory()
    new_location = WarehouseLocationFactory()
    old_item = WarehouseItemFactory(order_in=order, amount=10)

    count = 10
    new_items = [
        WarehouseItemSchema(
            id=-1,
            code="...",
            unit_of_measure=old_item.stock_product.unit_of_measure.name,
            created=timezone.now(),
            changed=timezone.now(),
            product=product_orm_to_schema(old_item.stock_product),
            location=location_orm_to_schema(new_location),
            amount=1,
            package=package_orm_to_schema(pkg),
        )
        for _ in range(count)
    ]

    result = warehouse_service.setup_tracking_for_inbound_order_item(
        order.code, old_item.code, new_items
    )
    assert WarehouseItem.objects.filter(code=old_item.code).first() is None
    assert result.code == order.code
    assert result.state == order.state
    assert len(result.items) == count
    for item in result.items:
        assert item.location.code == new_location.code
        assert item.code != old_item.code
        assert item.package.type == pkg.name
        assert item.product.code == old_item.stock_product.code


def test_setup_tracking_for_inbound_order_item_remaining(db):
    order = InboundWarehouseOrderFactory()
    pkg = PackageTypeFactory()
    # new_location = WarehouseLocationFactory()
    old_item = WarehouseItemFactory(order_in=order, amount=20)
    location = old_item.location

    count = 10
    new_items = [
        WarehouseItemSchema(
            id=-1,
            code="...",
            unit_of_measure=old_item.stock_product.unit_of_measure.name,
            created=timezone.now(),
            changed=timezone.now(),
            product=product_orm_to_schema(old_item.stock_product),
            location=location_orm_to_schema(location),
            amount=1,
            package=package_orm_to_schema(pkg),
        )
        for _ in range(count)
    ]

    result = warehouse_service.setup_tracking_for_inbound_order_item(
        order.code, old_item.code, new_items
    )
    old_item = WarehouseItem.objects.filter(code=old_item.code).first()
    assert old_item is not None
    assert old_item.amount == 10

    assert result.code == order.code
    assert result.state == order.state

    packaged_items = [item for item in result.items if item.package is not None]
    assert len(packaged_items) == count

    for item in packaged_items:
        assert item.location.code == location.code
        assert item.package.type == pkg.name
        assert item.product.code == old_item.stock_product.code

    unpackaged_items = [item for item in result.items if item.package is None]
    assert len(unpackaged_items) == 1
    for item in unpackaged_items:
        assert item.location.code == location.code
        assert item.package is None
        assert item.product.code == old_item.stock_product.code


def test_dissolve_inbound_order_item_create(db):
    """Dissolve and re-create the package-less item"""
    order = InboundWarehouseOrderFactory()
    pkg = PackageTypeFactory()
    packaged_item = WarehouseItemFactory(order_in=order, amount=10, package_type=pkg)

    warehouse_service.dissolve_inbound_order_item(order.code, packaged_item.code)

    order = InboundWarehouseOrder.objects.get(code=order.code)
    items = list(order.items.all())
    assert len(items) == 1
    item = items[0]
    assert item.location.code == packaged_item.location.code
    assert item.amount == 10
    assert item.package_type is None

    with pytest.raises(WarehouseItem.DoesNotExist):
        WarehouseItem.objects.get(code=packaged_item.code)


def test_dissolve_inbound_order_item_add(db):
    """Dissolve and add to an existing package-less item"""
    order = InboundWarehouseOrderFactory()
    pkg = PackageTypeFactory()
    product = StockProductFactory()
    # non-relevant item (should be ignored)
    WarehouseItemFactory(order_in=order, amount=99, package_type=None)
    package_less_item = WarehouseItemFactory(
        stock_product=product, order_in=order, amount=10, package_type=None
    )
    packaged_item = WarehouseItemFactory(
        stock_product=product, order_in=order, amount=10, package_type=pkg
    )

    warehouse_service.dissolve_inbound_order_item(order.code, packaged_item.code)

    order = InboundWarehouseOrder.objects.get(code=order.code)
    items = list(order.items.filter(stock_product=packaged_item.stock_product))
    assert len(items) == 1
    item = items[0]
    assert item.amount == 20
    assert item.location.code == package_less_item.location.code
    assert item.package_type is None

    with pytest.raises(WarehouseItem.DoesNotExist):
        WarehouseItem.objects.get(code=packaged_item.code)


def test_remove_from_order_to_credit_note(db):
    amount = 100
    unit_price = 99
    warehouse_order = CompleteOrderFactory(amount_and_unit_price=(amount, unit_price))
    item = warehouse_order.items.first()
    # product = StockProductFactory()
    # item = WarehouseItemFactory(order_in=order, stock_product=product, amount=100, package_type=None)

    credited_amount = 10
    w_order = warehouse_service.remove_from_order_to_credit_note(
        warehouse_order.code, item.code, credited_amount
    )
    credit_note = w_order.credit_note
    assert credit_note
    assert credit_note.state == CreditNoteState.DRAFT
    assert credit_note.order.code == warehouse_order.order.code
    assert len(credit_note.items) == 1

    credit_item = credit_note.items[0]
    assert credit_item.product.code == item.stock_product.code
    assert credit_item.amount == credited_amount
    assert credit_item.unit_price == unit_price

    war_item = WarehouseItem.objects.get(code=item.code)
    assert war_item.amount == amount - credited_amount


def test_remove_from_order_to_credit_note_all_gone(db):
    amount = 100
    warehouse_order = CompleteOrderFactory(amount_and_unit_price=(amount, 1))
    item = warehouse_order.items.first()

    credited_amount = amount
    w_order = warehouse_service.remove_from_order_to_credit_note(
        warehouse_order.code, item.code, credited_amount
    )
    assert len(w_order.credit_note.items) == 1

    credit_item = w_order.credit_note.items[0]
    assert credit_item.product.code == item.stock_product.code
    assert credit_item.amount == credited_amount

    assert not WarehouseItem.objects.filter(code=item.code).exists()


def test_putaway_item_simple(db):
    piece_uom = UnitOfMeasureFactory(name="KS")
    stock_product = StockProductFactory(unit_of_measure=piece_uom)
    new_location = WarehouseLocationFactory()

    war_order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)
    unpackaged = WarehouseItemFactory(
        stock_product=stock_product, order_in=war_order, amount=10
    )

    warehouse_service.putaway_item(unpackaged.code, war_order.code, new_location.code)

    loc = WarehouseLocation.objects.get(code=new_location.code)
    assert loc.items.count() == 1
    item = loc.items.first()
    assert item.amount == 10
    assert item.location.code == new_location.code
    assert item.package_type is None


def test_putaway_item_packaged(db):
    piece_uom = UnitOfMeasureFactory(name="KS")
    box_100 = PackageTypeFactory(name="B0100", unit_of_measure=piece_uom)
    stock_product = StockProductFactory(unit_of_measure=piece_uom)
    new_location = WarehouseLocationFactory()

    war_order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)
    packaged = WarehouseItemFactory(
        stock_product=stock_product,
        order_in=war_order,
        amount=100,
        package_type=box_100,
    )

    warehouse_service.putaway_item(packaged.code, war_order.code, new_location.code)

    loc = WarehouseLocation.objects.get(code=new_location.code)
    assert loc.items.count() == 1
    item = loc.items.first()
    assert item.amount == 100
    assert item.package_type == box_100


def test_putaway_item_unpackaged_merge(db):
    # untracked items containing the same stock product HAVE to have the same code!
    item_code = "111222333"
    piece_uom = UnitOfMeasureFactory(name="KS")
    stock_product = StockProductFactory(unit_of_measure=piece_uom)
    new_location = WarehouseLocationFactory()

    # new location already has the same untracked stock-product-item, it has to be merged
    WarehouseItemFactory(
        code=item_code, stock_product=stock_product, amount=50, location=new_location
    )

    war_order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)
    unpackaged = WarehouseItemFactory(
        code=item_code, stock_product=stock_product, order_in=war_order, amount=10
    )
    old_pk = unpackaged.pk

    warehouse_service.putaway_item(unpackaged.code, war_order.code, new_location.code)

    loc = WarehouseLocation.objects.get(code=new_location.code)
    assert loc.items.count() == 1
    item = loc.items.first()
    assert item.amount == (50 + 10)
    assert item.package_type is None

    with pytest.raises(WarehouseItem.DoesNotExist):
        assert WarehouseItem.objects.get(pk=old_pk)


@pytest.mark.parametrize(
    "state",
    [
        InboundWarehouseOrderState.DRAFT,
        InboundWarehouseOrderState.COMPLETED,
        InboundWarehouseOrderState.CANCELLED,
    ],
)
def test_putaway_item_invalid_order_state(db, state):
    new_location = WarehouseLocationFactory()
    war_order = InboundWarehouseOrderFactory(state=state)
    unpackaged = WarehouseItemFactory(order_in=war_order)

    with pytest.raises(WarehouseItemGenericError):
        warehouse_service.putaway_item(
            unpackaged.code, war_order.code, new_location.code
        )


def test_start_inbound_order(db):
    putaway_location = WarehouseLocationFactory(is_putaway=True)
    order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)
    to_be_moved = WarehouseItemFactory(order_in=order, location=putaway_location)
    WarehouseItemFactory.create_batch(9, order_in=order, location=putaway_location)

    new_location = WarehouseLocationFactory(is_putaway=False)

    warehouse_service.putaway_item(to_be_moved.code, order.code, new_location.code)

    order.refresh_from_db()
    assert order.state == InboundWarehouseOrderState.STARTED
    assert order.items.filter(location__is_putaway=True).count() == 9


def test_complete_inbound_order(db):
    putaway_location = WarehouseLocationFactory(is_putaway=True)
    order = InboundWarehouseOrderFactory(state=InboundWarehouseOrderState.PENDING)
    to_be_moved_1 = WarehouseItemFactory(order_in=order, location=putaway_location)
    to_be_moved_2 = WarehouseItemFactory(order_in=order, location=putaway_location)

    new_location = WarehouseLocationFactory(is_putaway=False)

    warehouse_service.putaway_item(to_be_moved_1.code, order.code, new_location.code)
    order.refresh_from_db()
    assert order.state == InboundWarehouseOrderState.STARTED

    warehouse_service.putaway_item(to_be_moved_2.code, order.code, new_location.code)
    order.refresh_from_db()
    assert order.state == InboundWarehouseOrderState.COMPLETED
