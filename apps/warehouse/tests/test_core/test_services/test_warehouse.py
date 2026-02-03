from typing import cast

import pytest
from django.utils import timezone

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
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    WarehouseLocation,
    WarehouseItem,
    InboundWarehouseOrder,
)
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
)
from apps.warehouse.tests.factories.packaging import PackageTypeFactory
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    WarehouseItemFactory,
    InboundWarehouseOrderFactory,
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
