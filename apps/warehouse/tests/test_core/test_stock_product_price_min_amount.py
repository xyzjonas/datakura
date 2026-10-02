from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.warehouse.core.services.products import StockProductsService
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.product import (
    StockProductFactory,
    StockProductPriceFactory,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "first, second, allowed",
    [
        (None, None, False),
        (10, 10, False),
        (None, 10, True),
        (10, 20, True),
    ],
)
def test_price_uniqueness_per_product_customer_and_min_amount(first, second, allowed):
    product, customer = StockProductFactory(), CustomerFactory()
    StockProductPriceFactory(product=product, customer=customer, min_amount=first)

    def duplicate():
        with transaction.atomic():
            StockProductPriceFactory(
                product=product, customer=customer, min_amount=second
            )

    if allowed:
        duplicate()
    else:
        with pytest.raises(IntegrityError):
            duplicate()


@pytest.mark.django_db
@pytest.mark.parametrize("min_amount", [0, -1])
def test_min_amount_must_be_positive(min_amount):
    with pytest.raises(IntegrityError), transaction.atomic():
        StockProductPriceFactory(min_amount=min_amount)


@pytest.mark.django_db
def test_selling_price_lookup_ignores_quantity_limited_prices():
    product, customer = StockProductFactory(base_price=100), CustomerFactory()
    StockProductPriceFactory(
        product=product, customer=customer, fixed_price=10, min_amount=5
    )

    lookup = StockProductsService.get_selling_price_lookup(product.code, customer.code)
    assert lookup.final_price == 100

    StockProductPriceFactory(product=product, customer=customer, fixed_price=60)
    lookup = StockProductsService.get_selling_price_lookup(product.code, customer.code)
    assert lookup.final_price == 60 and lookup.source == "CUSTOMER_OVERRIDE"


@pytest.mark.django_db
def test_upsert_override_touches_only_the_unlimited_price():
    product, customer = StockProductFactory(), CustomerFactory()
    limited = StockProductPriceFactory(
        product=product, customer=customer, fixed_price=10, min_amount=5
    )
    from apps.warehouse.core.schemas.product import CustomerPriceOverrideUpsertSchema

    params = CustomerPriceOverrideUpsertSchema(
        customer_code=customer.code, fixed_price=50
    )
    StockProductsService.upsert_customer_price_override(product.code, params)
    StockProductsService.upsert_customer_price_override(product.code, params)

    limited.refresh_from_db()
    assert limited.fixed_price == Decimal("10")
    assert product.dynamic_prices.count() == 2
