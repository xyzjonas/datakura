"""Helpers behind the query optimizations: barcode prefetch and batched pricing."""

from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.warehouse.core.services.outbound_common import with_pricing_details
from apps.warehouse.core.services.products import StockProductsService
from apps.warehouse.core.transformation import outbound_order_orm_to_schema
from apps.warehouse.models.barcode import BarcodeType, prefetch_barcodes
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import Batch
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.order import (
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.packaging import BatchFactory
from apps.warehouse.tests.factories.product import (
    PriceGroupFactory,
    StockProductFactory,
    StockProductPriceFactory,
)
from apps.warehouse.tests.factories.settings import GlobalSettingsFactory


@pytest.mark.django_db
def test_prefetch_barcodes_mixed_models_one_query_each() -> None:
    product, bare_product = StockProductFactory.it(), StockProductFactory.it()
    batch = BatchFactory.it()
    product.attach_barcode("P-PRIMARY", BarcodeType.EAN13, is_primary=True)
    product.attach_barcode("P-OTHER", BarcodeType.CUSTOM)
    batch.attach_barcode("B-PRIMARY", BarcodeType.CUSTOM, is_primary=True)

    objs = [product, bare_product, batch, None]
    with CaptureQueriesContext(connection) as ctx:
        prefetch_barcodes(objs)
    assert len(ctx) <= 4  # content types (cached or not) + one query per model

    with CaptureQueriesContext(connection) as ctx:
        assert [b.code for b in product.barcode_list()] == ["P-PRIMARY", "P-OTHER"]
        assert product.get_primary_barcode().code == "P-PRIMARY"  # type: ignore[union-attr]
        assert bare_product.barcode_list() == []
        assert bare_product.get_primary_barcode() is None
        assert batch.get_primary_barcode().code == "B-PRIMARY"  # type: ignore[union-attr]
    assert len(ctx) == 0


@pytest.mark.django_db
def test_prefetch_barcodes_is_idempotent_and_handles_empty_input() -> None:
    product = StockProductFactory.it()
    product.attach_barcode("P-1", BarcodeType.EAN13, is_primary=True)
    prefetch_barcodes([])
    prefetch_barcodes([product])
    with CaptureQueriesContext(connection) as ctx:
        prefetch_barcodes([product])  # already loaded: nothing to do
    assert len(ctx) == 0


@pytest.mark.django_db
def test_barcode_accessors_without_prefetch_hit_the_db() -> None:
    product = StockProductFactory.it()
    product.attach_barcode("P-1", BarcodeType.EAN13, is_primary=True)
    assert [b.code for b in product.barcode_list()] == ["P-1"]
    # not cached: a barcode attached afterwards is seen
    product.attach_barcode("P-2", BarcodeType.CUSTOM)
    assert {b.code for b in product.barcode_list()} == {"P-1", "P-2"}


@pytest.mark.django_db
def test_with_barcodes_queryset_loads_barcodes_in_one_extra_query() -> None:
    products = [StockProductFactory.it() for _ in range(3)]
    for product in products:
        product.attach_barcode(f"EAN-{product.pk}", is_primary=True)

    with CaptureQueriesContext(connection) as ctx:
        loaded = list(StockProduct.objects.with_barcodes())
        codes = [p.get_primary_barcode().code for p in loaded]  # type: ignore[union-attr]
    assert len(ctx) <= 3
    assert sorted(codes) == sorted(f"EAN-{p.pk}" for p in products)
    assert Batch.objects.with_barcodes().count() == 0  # chaining keeps working


@pytest.mark.django_db
def test_get_customer_overrides_only_unlimited_prices_of_that_customer() -> None:
    customer, other = CustomerFactory.it(), CustomerFactory.it()
    plain, limited_only, untouched = [StockProductFactory.it() for _ in range(3)]
    override = StockProductPriceFactory(product=plain, customer=customer, fixed_price=5)
    StockProductPriceFactory(
        product=plain, customer=customer, fixed_price=1, min_amount=10
    )
    StockProductPriceFactory(product=limited_only, customer=customer, min_amount=3)
    StockProductPriceFactory(product=untouched, customer=other, fixed_price=2)

    result = StockProductsService.get_customer_overrides(
        customer, [plain, limited_only, untouched]
    )
    assert result == {plain.pk: override}
    assert StockProductsService.get_customer_overrides(customer, []) == {}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "scenario",
    ["override", "group_discount", "no_discount_product", "base_price", "minimum"],
)
def test_with_pricing_details_matches_single_item_lookup(scenario: str) -> None:
    """Batched pricing has to give the very same numbers as the per-product lookup."""
    GlobalSettingsFactory(
        minimum_item_value=Decimal("1000" if scenario == "minimum" else "0")
    )
    group = (
        PriceGroupFactory(discount_percent=Decimal("20"))
        if scenario in ("group_discount", "no_discount_product")
        else None
    )
    customer = CustomerFactory.it(discount_group=group)
    order = OutboundOrderFactory.it(customer=customer)
    products = [
        StockProductFactory.it(
            base_price=Decimal("100"), no_discount=scenario == "no_discount_product"
        )
        for _ in range(3)
    ]
    for i, product in enumerate(products):
        if scenario == "override" and i < 2:  # the third falls back to base price
            StockProductPriceFactory(
                product=product, customer=customer, fixed_price=Decimal(50 + i)
            )
        OutboundOrderItemFactory.it(
            order=order,
            stock_product=product,
            amount=1,
            unit_price=10,
            # at the minimum item value: the reason gets the explanation appended
            total_price=1000 if scenario == "minimum" else 10,
        )

    order = type(order).objects.get(pk=order.pk)
    schema = with_pricing_details(outbound_order_orm_to_schema(order), order)

    assert len(schema.items) == 3
    for item in schema.items:
        expected = StockProductsService.get_selling_price_lookup(
            item.product.code, customer.code
        )
        details = item.pricing_details
        assert details is not None
        assert details.suggested_unit_price == expected.final_price
        assert details.discount_percent == expected.discount_percent
        assert details.source == expected.source
        assert details.base_price == expected.base_price
        assert (details.reason != expected.reason) == (scenario == "minimum")


@pytest.mark.django_db
def test_with_pricing_details_empty_order() -> None:
    order = OutboundOrderFactory.it()
    schema = with_pricing_details(outbound_order_orm_to_schema(order), order)
    assert schema.items == []
