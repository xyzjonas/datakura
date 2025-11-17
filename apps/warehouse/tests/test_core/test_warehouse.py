from typing import cast

import pytest

from apps.warehouse.core.warehouse import (
    get_warehouse_availability,
    get_total_availability,
)
from apps.warehouse.models.product import StockProduct
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import WarehouseItemFactory


@pytest.mark.parametrize("items_amount, amount", [(3, 99), (0, 10), (3, 1.2)])
def test_get_warehouse_availability(db, items_amount, amount):
    product = cast(StockProduct, StockProductFactory())
    WarehouseItemFactory.create_batch(
        items_amount, amount=amount, stock_product=product
    )
    assert get_warehouse_availability(product.code) == pytest.approx(
        items_amount * amount
    )


@pytest.mark.parametrize("items_amount, amount", [(10, 10), (0, 10), (3, 1.2)])
def test_get_total_availability(db, items_amount, amount):
    product = cast(StockProduct, StockProductFactory())
    WarehouseItemFactory.create_batch(
        items_amount, amount=amount, stock_product=product
    )
    result = get_total_availability(product.code)
    assert result.total_amount == pytest.approx(items_amount * amount)
    assert result.available_amount == pytest.approx(items_amount * amount)
