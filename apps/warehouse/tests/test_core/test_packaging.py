from typing import cast

from apps.warehouse.core.packaging import get_package_amount_in_product_uom
from apps.warehouse.models.packaging import PackageType
from apps.warehouse.models.product import StockProduct
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.units import UnitOfMeasureFactory


def test_get_package_amount_in_product_uom(db):
    each = UnitOfMeasureFactory(name="Each", amount_of_base_uom=1)
    hundred = UnitOfMeasureFactory(name="100", amount_of_base_uom=100, base_uom=each)
    package_type = PackageType(name="BOX500", amount=500, unit_of_measure=each)
    product = cast(StockProduct, StockProductFactory(unit_of_measure=hundred))

    assert get_package_amount_in_product_uom(package_type, product) == 5

    dozen = UnitOfMeasureFactory(name="dozen", amount_of_base_uom=12, base_uom=each)
    egg = StockProduct(name="egg", unit_of_measure=each)
    egg_box = PackageType(name="12 Eggs box", amount=1, unit_of_measure=dozen)

    assert get_package_amount_in_product_uom(egg_box, egg) == 12
