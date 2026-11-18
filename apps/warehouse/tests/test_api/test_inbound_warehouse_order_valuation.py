from decimal import Decimal

import pytest
from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.warehouse import routes
from apps.warehouse.models.warehouse import InboundWarehouseOrderState
from apps.warehouse.tests.factories.order import InboundOrderFactory
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    InboundWarehouseOrderItemFactory,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def make_order(lines=(), *, frozen_currency=None, parent_currency="CZK", **kwargs):
    w_order = InboundWarehouseOrderFactory.it(
        order=InboundOrderFactory.it(currency=parent_currency),
        state=kwargs.pop("state", InboundWarehouseOrderState.PENDING),
        **kwargs,
    )
    if frozen_currency:
        w_order.currency = frozen_currency
        w_order.valued_at = timezone.now()
        w_order.save()
    for amount, unit in lines:
        InboundWarehouseOrderItemFactory(
            warehouse_order=w_order,
            stock_product=StockProductFactory(),
            amount=Decimal(amount),
            unit_price_at_receipt=Decimal(unit),
        )
    return w_order


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        ((("2", "10"), ("3", "5.5")), "36.5000"),
        ((("1", "0"),), "0.0000"),
        ((), "0.0000"),
        ((("0.5", "3"),), "1.5000"),
    ],
)
def test_detail_returns_total_price_at_receipt(db, client, lines, expected):
    w_order = make_order(lines)

    res = client.get(f"orders-incoming/{w_order.code}")

    assert res.status_code == 200
    assert Decimal(res.json()["data"]["total_price_at_receipt"]) == Decimal(expected)


@pytest.mark.parametrize(
    ("frozen", "parent", "expected"),
    [
        (None, "EUR", "EUR"),  # not valued yet -> parent order currency
        ("EUR", "USD", "EUR"),  # frozen currency wins over later parent changes
        ("CZK", "CZK", "CZK"),
    ],
)
def test_detail_currency_is_frozen_once_valued(db, client, frozen, parent, expected):
    w_order = make_order((("1", "1"),), frozen_currency=frozen, parent_currency=parent)

    res = client.get(f"orders-incoming/{w_order.code}")

    assert res.json()["data"]["currency"] == expected


def test_list_returns_total_price_per_order(db, client):
    cheap = make_order((("1", "2"),))
    dear = make_order((("10", "10"),), frozen_currency="EUR")

    res = client.get("orders-incoming")

    assert res.status_code == 200
    by_code = {row["code"]: row for row in res.json()["data"]}
    assert Decimal(by_code[cheap.code]["total_price_at_receipt"]) == Decimal("2")
    assert Decimal(by_code[dear.code]["total_price_at_receipt"]) == Decimal("100")
    assert by_code[dear.code]["currency"] == "EUR"
