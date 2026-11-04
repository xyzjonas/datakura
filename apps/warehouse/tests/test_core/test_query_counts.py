"""
Query-count regression tests: the number of queries needed to serialize an order
must not grow with the number of its items (no N+1).
"""

from collections.abc import Callable

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from ninja.testing import TestClient

from apps.warehouse.api.routes.analytics import routes as analytics_routes
from apps.warehouse.api.routes.inbound_orders import routes as inbound_routes
from apps.warehouse.api.routes.outbound_calculations import (
    routes as calculation_routes,
)
from apps.warehouse.api.routes.outbound_orders import routes as outbound_routes
from apps.warehouse.api.routes.warehouse import routes as warehouse_routes
from apps.warehouse.core.services.inventory_snapshots import inventory_snapshot_service
from apps.warehouse.models.barcode import BarcodeType
from apps.warehouse.models.orders import OutboundOrder
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
    OutboundCalculationFactory,
    OutboundCalculationItemFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.packaging import BatchFactory, PackageTypeFactory
from apps.warehouse.tests.factories.product import (
    StockProductFactory,
    StockProductPriceFactory,
)
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    InboundWarehouseOrderItemFactory,
    OutboundWarehouseOrderItemFactory,
    WarehouseItemFactory,
    WarehouseMovementFactory,
    WarehouseOrderOutFactory,
)

SMALL = 2
LARGE = 8


def _make_product(customer=None):
    product = StockProductFactory.it()
    product.attach_barcode(f"EAN-{product.code}", BarcodeType.EAN13, is_primary=True)
    product.attach_barcode(f"ALT-{product.code}", BarcodeType.CUSTOM)
    if customer is not None:
        StockProductPriceFactory(product=product, customer=customer)
    return product


def _make_batch():
    batch = BatchFactory.it()
    batch.attach_barcode(f"BATCH-{batch.pk}", BarcodeType.CUSTOM, is_primary=True)
    return batch


def _count_queries(call: Callable[[], object]) -> int:
    with CaptureQueriesContext(connection) as ctx:
        call()
    return len(ctx)


def _assert_constant_queries(build: Callable[[int], Callable[[], object]]) -> None:
    """`build(n)` seeds `n` items and returns the (read-only) call to measure."""
    small_call = build(SMALL)
    small_call()  # warm up ContentType cache etc.
    small = _count_queries(small_call)
    large_call = build(LARGE)  # seeded on top: list endpoints now see more rows
    large = _count_queries(large_call)
    assert large == small, (
        f"queries grow with items: {small} for {SMALL} items vs {large} for {LARGE}"
    )


def _outbound_order(n_items: int) -> OutboundOrder:
    customer = CustomerFactory.it()
    order = OutboundOrderFactory.it(customer=customer)
    package_type = PackageTypeFactory()
    for _ in range(n_items):
        OutboundOrderItemFactory.it(
            order=order,
            stock_product=_make_product(customer),
            desired_batch=_make_batch(),
            desired_package_type=package_type,
        )
    return order


@pytest.mark.django_db
def test_outbound_order_detail_query_count_is_constant() -> None:
    client = TestClient(outbound_routes)

    def build(n: int):
        code = _outbound_order(n).code
        return lambda: client.get(f"/{code}").json()

    _assert_constant_queries(build)


@pytest.mark.django_db
def test_outbound_order_detail_pricing_details_are_complete() -> None:
    client = TestClient(outbound_routes)
    order = _outbound_order(3)
    items = client.get(f"/{order.code}").json()["data"]["items"]
    assert len(items) == 3
    for item in items:
        assert item["pricing_details"]["source"] == "CUSTOMER_OVERRIDE"
        assert item["product"]["primary_barcode"]["code"].startswith("EAN-")
        assert len(item["product"]["barcodes"]) == 2
        assert item["desired_batch_code"].startswith("BATCH-")


@pytest.mark.django_db
def test_outbound_order_list_query_count_is_constant() -> None:
    client = TestClient(outbound_routes)

    def build(n: int):
        # the list is paginated, so grow the number of orders *and* items per order
        for _ in range(n):
            _outbound_order(n)
        return lambda: client.get("", query_params={"page_size": 50}).json()

    _assert_constant_queries(build)


@pytest.mark.django_db
def test_outbound_calculation_detail_query_count_is_constant() -> None:
    client = TestClient(calculation_routes)

    def build(n: int):
        customer = CustomerFactory.it()
        calc = OutboundCalculationFactory.it(customer=customer)
        for _ in range(n):
            OutboundCalculationItemFactory.it(
                calculation=calc,
                stock_product=_make_product(customer),
                desired_batch=_make_batch(),
            )
        return lambda: client.get(f"/{calc.code}").json()

    _assert_constant_queries(build)


@pytest.mark.django_db
def test_inbound_order_detail_query_count_is_constant() -> None:
    client = TestClient(inbound_routes)

    def build(n: int):
        order = InboundOrderFactory.it()
        for _ in range(n):
            InboundOrderItemFactory.it(order=order, stock_product=_make_product())
        return lambda: client.get(f"/{order.code}").json()

    _assert_constant_queries(build)


@pytest.mark.django_db
def test_inbound_order_list_query_count_is_constant() -> None:
    client = TestClient(inbound_routes)

    def build(n: int):
        for _ in range(n):
            order = InboundOrderFactory.it()
            for _ in range(n):
                InboundOrderItemFactory.it(order=order, stock_product=_make_product())
        return lambda: client.get("", query_params={"page_size": 50}).json()

    _assert_constant_queries(build)


@pytest.mark.django_db
def test_outbound_warehouse_order_detail_query_count_is_constant() -> None:
    client = TestClient(warehouse_routes)

    def build(n: int):
        order = OutboundOrderFactory.it()
        wo = WarehouseOrderOutFactory(order=order)
        for i in range(n):
            item = OutboundOrderItemFactory.it(
                order=order, stock_product=_make_product(), desired_batch=_make_batch()
            )
            stock = WarehouseItemFactory(
                stock_product=item.stock_product,
                batch=item.desired_batch,
                package_type=PackageTypeFactory(),
                amount=item.amount,
            )
            OutboundWarehouseOrderItemFactory(
                warehouse_order=wo,
                source_order_item=item,
                desired_batch=item.desired_batch,
                warehouse_item=stock,
                index=i,
            )
            WarehouseMovementFactory(
                stock_product=item.stock_product,
                item=stock,
                outbound_order_code=wo,
            )
        return lambda: client.get(f"orders-outgoing/{wo.code}").json()

    _assert_constant_queries(build)


@pytest.mark.django_db
def test_outbound_warehouse_order_list_query_count_is_constant() -> None:
    client = TestClient(warehouse_routes)

    def build(n: int):
        for _ in range(n):
            order = OutboundOrderFactory.it()
            wo = WarehouseOrderOutFactory(order=order)
            for i in range(n):
                item = OutboundOrderItemFactory.it(
                    order=order, stock_product=_make_product()
                )
                OutboundWarehouseOrderItemFactory(
                    warehouse_order=wo, source_order_item=item, index=i
                )
        return lambda: client.get(
            "orders-outgoing", query_params={"page_size": 50}
        ).json()

    _assert_constant_queries(build)


@pytest.mark.django_db
def test_outbound_calculation_list_query_count_is_constant() -> None:
    client = TestClient(calculation_routes)

    def build(n: int):
        for _ in range(n):
            customer = CustomerFactory.it()
            calc = OutboundCalculationFactory.it(customer=customer)
            for _ in range(n):
                OutboundCalculationItemFactory.it(
                    calculation=calc,
                    stock_product=_make_product(customer),
                    desired_batch=_make_batch(),
                )
        return lambda: client.get("", query_params={"page_size": 50}).json()

    _assert_constant_queries(build)


def _inbound_warehouse_order(n_items: int):
    order = InboundOrderFactory.it()
    wo = InboundWarehouseOrderFactory(order=order)
    for i in range(n_items):
        product = _make_product()
        InboundOrderItemFactory.it(order=order, stock_product=product)
        order_item = InboundWarehouseOrderItemFactory(
            warehouse_order=wo, stock_product=product, index=i
        )
        stock = WarehouseItemFactory(
            stock_product=product,
            order_in=wo,
            source_order_item=order_item,
            package_type=PackageTypeFactory(),
            batch=_make_batch(),
            amount=order_item.amount,
        )
        WarehouseMovementFactory(stock_product=product, item=stock)
    return wo


@pytest.mark.django_db
def test_inbound_warehouse_order_detail_query_count_is_constant() -> None:
    client = TestClient(warehouse_routes)

    def build(n: int):
        code = _inbound_warehouse_order(n).code
        return lambda: client.get(f"orders-incoming/{code}").json()

    _assert_constant_queries(build)


@pytest.mark.django_db
def test_inbound_warehouse_order_list_query_count_is_constant() -> None:
    client = TestClient(warehouse_routes)

    def build(n: int):
        for _ in range(n):
            _inbound_warehouse_order(n)
        return lambda: client.get(
            "orders-incoming", query_params={"page_size": 50}
        ).json()

    _assert_constant_queries(build)


@pytest.mark.django_db
def test_outbound_order_with_calculation_credit_note_and_warehouse_orders_is_constant() -> (
    None
):
    """Header relations (calculation, warehouse orders + children) must not add per-order queries."""
    client = TestClient(outbound_routes)

    def build(n: int):
        for _ in range(n):
            order = _outbound_order(n)
            OutboundCalculationFactory.it(order=order, customer=order.customer)
            parent = WarehouseOrderOutFactory(order=order)
            WarehouseOrderOutFactory(order=order, primary_order=parent)
        return lambda: client.get("", query_params={"page_size": 50}).json()

    _assert_constant_queries(build)


@pytest.mark.django_db
def test_inventory_snapshot_detail_query_count_is_constant() -> None:
    client = TestClient(analytics_routes)

    def build(n: int):
        for _ in range(n):
            WarehouseItemFactory(stock_product=_make_product(), amount=1, order_in=None)
        snapshot = inventory_snapshot_service.create_snapshot(force=True)
        assert snapshot.line_count >= n
        return lambda: client.get(f"/inventory-snapshots/{snapshot.id}").json()

    _assert_constant_queries(build)


@pytest.mark.django_db
def test_inventory_snapshot_items_query_count_is_constant() -> None:
    client = TestClient(analytics_routes)

    def build(n: int):
        for _ in range(n):
            WarehouseItemFactory(stock_product=_make_product(), amount=1, order_in=None)
        snapshot = inventory_snapshot_service.create_snapshot(force=True)
        return lambda: client.get(f"/inventory-snapshots/{snapshot.id}/items").json()

    _assert_constant_queries(build)


@pytest.mark.django_db
def test_inventory_snapshot_creation_query_count_is_constant() -> None:
    def build(n: int):
        for _ in range(n):
            WarehouseItemFactory(stock_product=_make_product(), amount=1, order_in=None)
        return lambda: inventory_snapshot_service.create_snapshot(force=True)

    _assert_constant_queries(build)
