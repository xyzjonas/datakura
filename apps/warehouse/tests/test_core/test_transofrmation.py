import pytest

from apps.warehouse.core.transformation import warehouse_item_orm_to_schema
from apps.warehouse.tests.factories.packaging import PackageTypeFactory, PackageFactory
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.units import UnitOfMeasureFactory
from apps.warehouse.tests.factories.warehouse import WarehouseItemFactory


@pytest.mark.django_db
def test_warehouse_item_transform_with_pkg_same_uom_as_product():
    base_uom = UnitOfMeasureFactory(name="KS")
    unit_of_measure = UnitOfMeasureFactory(
        name="100ks", base_uom=base_uom, amount_of_base_uom=100
    )
    package = PackageFactory(
        type=PackageTypeFactory(
            unit_of_measure=unit_of_measure, amount=4, name="PAK-400KS"
        )
    )
    item_model = WarehouseItemFactory(
        amount=1.2,
        package=package,
        stock_product=StockProductFactory(unit_of_measure=unit_of_measure),
    )
    transformed = warehouse_item_orm_to_schema(item_model)
    assert transformed.amount == 1.2
    assert transformed.package.amount == 4


@pytest.mark.django_db
def test_warehouse_item_transform_with_pkg_pkg_is_base_uom():
    base_uom = UnitOfMeasureFactory(name="KS")
    unit_of_measure = UnitOfMeasureFactory(
        name="100ks", base_uom=base_uom, amount_of_base_uom=100
    )
    package = PackageFactory(
        type=PackageTypeFactory(unit_of_measure=base_uom, amount=400, name="PAK-400KS")
    )
    item_model = WarehouseItemFactory(
        amount=1.2,
        package=package,
        stock_product=StockProductFactory(unit_of_measure=unit_of_measure),
    )
    transformed = warehouse_item_orm_to_schema(item_model)
    assert transformed.amount == 1.2
    assert transformed.package.amount == 4


@pytest.mark.django_db
def test_warehouse_item_transform_with_pkg_product_is_base_uom():
    base_uom = UnitOfMeasureFactory(name="KS")
    unit_of_measure = UnitOfMeasureFactory(
        name="100ks", base_uom=base_uom, amount_of_base_uom=100
    )
    package = PackageFactory(
        type=PackageTypeFactory(
            unit_of_measure=unit_of_measure, amount=4, name="PAK-400KS"
        )
    )
    item_model = WarehouseItemFactory(
        amount=120,
        package=package,
        stock_product=StockProductFactory(unit_of_measure=base_uom),
    )
    transformed = warehouse_item_orm_to_schema(item_model)
    assert transformed.amount == 120
    assert transformed.package.amount == 400
