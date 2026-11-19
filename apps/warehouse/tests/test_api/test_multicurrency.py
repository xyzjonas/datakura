from decimal import Decimal
from typing import cast

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes import customer as customer_routes
from apps.warehouse.api.routes import invoices as invoice_routes
from apps.warehouse.api.routes import outbound_calculations as calculation_routes
from apps.warehouse.api.routes import outbound_orders as order_routes
from apps.warehouse.api.routes import settings as settings_routes
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.orders import OutboundOrder, OutboundOrderItem
from apps.warehouse.models.settings import CurrencyRate, GlobalSettings
from apps.warehouse.tests.factories.customer import (
    CustomerFactory,
    CustomerGroupFactory,
)
from apps.warehouse.tests.factories.order import (
    InvoicePaymentMethodFactory,
    OutboundCalculationFactory,
    OutboundCalculationItemFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.settings import (
    CurrencyRateFactory,
    GlobalSettingsFactory,
)
from apps.warehouse.tests.factories.warehouse import WarehouseOrderOutFactory
from apps.warehouse.models.warehouse import OutboundWarehouseOrderState


@pytest.fixture
def orders() -> TestClient:
    return TestClient(order_routes.routes)


@pytest.fixture
def calculations() -> TestClient:
    return TestClient(calculation_routes.routes)


@pytest.fixture
def settings_client() -> TestClient:
    return TestClient(settings_routes.routes)


def _header(customer, **extra) -> dict:
    return {
        "customer_code": customer.code,
        "customer_name": customer.name,
        **extra,
    }


# --- settings: base currency + rates --- #


def test_settings_default_to_czk_without_rates(db, settings_client) -> None:
    data = settings_client.get("").json()["data"]

    assert data["base_currency"] == "CZK"
    assert data["supported_currencies"] == ["CZK", "EUR", "PLN"]
    assert data["exchange_rates"] == []


def test_update_exchange_rates_upserts_and_keeps_others(db, settings_client) -> None:
    CurrencyRateFactory(currency="PLN", rate=Decimal("5.8"))

    response = settings_client.put(
        "", json={"exchange_rates": [{"currency": "EUR", "rate": 24.34}]}
    )
    assert response.status_code == 200
    settings_client.put(
        "", json={"exchange_rates": [{"currency": "EUR", "rate": 25.1}]}
    )

    rates = {r.currency: r.rate for r in CurrencyRate.objects.all()}
    assert rates == {"EUR": Decimal("25.1"), "PLN": Decimal("5.8")}
    assert [r["currency"] for r in response.json()["data"]["exchange_rates"]] == [
        "EUR",
        "PLN",
    ]


@pytest.mark.parametrize("rate", [0, -1, 1_000_000])
def test_update_exchange_rates_rejects_out_of_range_rate(
    db, settings_client, rate
) -> None:
    response = settings_client.put(
        "", json={"exchange_rates": [{"currency": "EUR", "rate": rate}]}
    )

    assert response.status_code == 422
    assert not CurrencyRate.objects.exists()


@pytest.mark.parametrize(
    "currency, base",
    [("USD", "CZK"), ("CZK", "CZK"), ("EUR", "EUR")],
    ids=["unsupported", "base-has-no-rate", "base-has-no-rate-eur"],
)
def test_update_exchange_rates_rejects_wrong_currency(
    db, settings_client, currency, base
) -> None:
    GlobalSettingsFactory(base_currency=base)

    with pytest.raises(WarehouseItemBadRequestError):
        settings_client.put(
            "", json={"exchange_rates": [{"currency": currency, "rate": 2}]}
        )


def test_change_base_currency_drops_old_rates(db, settings_client) -> None:
    CurrencyRateFactory(currency="EUR")

    response = settings_client.put("", json={"base_currency": "EUR"})

    assert response.status_code == 200
    assert response.json()["data"]["base_currency"] == "EUR"
    assert GlobalSettings.load().base_currency == "EUR"
    assert not CurrencyRate.objects.exists()


def test_same_base_currency_keeps_rates(db, settings_client) -> None:
    CurrencyRateFactory(currency="EUR")

    settings_client.put("", json={"base_currency": "CZK"})

    assert CurrencyRate.objects.count() == 1


def test_unsupported_base_currency_is_rejected(db, settings_client) -> None:
    with pytest.raises(WarehouseItemBadRequestError):
        settings_client.put("", json={"base_currency": "USD"})

    assert GlobalSettings.load().base_currency == "CZK"


# --- customers --- #


def test_customer_currency_defaults_to_null_and_can_be_set(db) -> None:
    client = TestClient(customer_routes.routes)
    customer = cast(Customer, CustomerFactory(customer_group=CustomerGroupFactory()))
    payload = {
        "code": customer.code,
        "name": customer.name,
        "customer_type": customer.customer_type,
        "price_type": customer.price_type,
        "customer_group_code": customer.customer_group.code,
    }

    assert client.get(f"/{customer.code}").json()["data"]["currency"] is None

    response = client.put(f"/{customer.code}", json={**payload, "currency": "EUR"})
    assert response.json()["data"]["currency"] == "EUR"

    response = client.put(f"/{customer.code}", json={**payload, "currency": ""})
    assert response.json()["data"]["currency"] is None


def test_customer_currency_must_be_supported(db) -> None:
    client = TestClient(customer_routes.routes)
    customer = cast(Customer, CustomerFactory(customer_group=CustomerGroupFactory()))

    with pytest.raises(WarehouseItemBadRequestError):
        client.put(
            f"/{customer.code}",
            json={
                "code": customer.code,
                "name": customer.name,
                "customer_type": customer.customer_type,
                "price_type": customer.price_type,
                "customer_group_code": customer.customer_group.code,
                "currency": "USD",
            },
        )


# --- order header --- #


def test_order_defaults_to_base_currency(db, orders) -> None:
    customer = CustomerFactory()

    data = orders.post("", json=_header(customer)).json()["data"]

    assert (data["currency"], data["document_currency"]) == ("CZK", "CZK")
    assert data["exchange_rate"] == 1


def test_order_follows_the_customer_currency(db, orders) -> None:
    CurrencyRateFactory(currency="EUR", rate=Decimal("24.5"))
    customer = CustomerFactory(currency="EUR")

    data = orders.post("", json=_header(customer)).json()["data"]

    # calculations stay in CZK, the document is in EUR with the frozen rate
    assert (data["currency"], data["document_currency"]) == ("CZK", "EUR")
    assert data["exchange_rate"] == 24.5


def test_order_currency_can_be_overridden_per_order(db, orders) -> None:
    CurrencyRateFactory(currency="PLN", rate=Decimal("5.8"))
    customer = CustomerFactory(currency="EUR")

    data = orders.post("", json=_header(customer, document_currency="PLN")).json()[
        "data"
    ]

    assert data["document_currency"] == "PLN"
    assert data["exchange_rate"] == 5.8


def test_order_in_foreign_currency_needs_a_rate(db, orders) -> None:
    customer = CustomerFactory(currency="EUR")

    with pytest.raises(WarehouseItemBadRequestError, match="exchange rate"):
        orders.post("", json=_header(customer))

    assert not OutboundOrder.objects.exists()


def test_order_rate_is_frozen_when_rates_change(db, orders) -> None:
    CurrencyRateFactory(currency="EUR", rate=Decimal("25"))
    customer = CustomerFactory(currency="EUR")
    code = orders.post("", json=_header(customer)).json()["data"]["code"]
    orders.post(
        f"/{code}/items",
        json={
            "product_code": StockProductFactory().code,
            "product_name": "x",
            "amount": 2,
            "document_total_price": 20,
        },
    )

    CurrencyRate.objects.update(rate=Decimal("30"))
    # editing the header with the same currency does not re-freeze the rate
    data = orders.put(f"/{code}", json=_header(customer, note="n")).json()["data"]

    assert data["exchange_rate"] == 25
    item = data["items"][0]
    assert (item["document_total_price"], item["total_price"]) == (20, 500)


def test_changing_order_currency_refreezes_rate_and_reprices_items(db, orders) -> None:
    CurrencyRateFactory(currency="EUR", rate=Decimal("25"))
    CurrencyRateFactory(currency="PLN", rate=Decimal("5"))
    customer = CustomerFactory()
    order = OutboundOrderFactory.it(customer=customer)
    OutboundOrderItemFactory.it(
        order=order, amount=Decimal("2"), unit_price=Decimal("50"), total_price=100
    )

    data = orders.put(
        f"/{order.code}", json=_header(customer, document_currency="EUR")
    ).json()["data"]
    assert data["document_currency"] == "EUR"
    assert data["exchange_rate"] == 25
    item = data["items"][0]
    # base prices are untouched, EUR ones derived
    assert (item["total_price"], item["unit_price"]) == (100, 50)
    assert (item["document_total_price"], item["document_unit_price"]) == (4, 2)

    data = orders.put(
        f"/{order.code}", json=_header(customer, document_currency="CZK")
    ).json()["data"]
    assert (data["document_currency"], data["exchange_rate"]) == ("CZK", 1)
    assert data["items"][0]["document_total_price"] == 100
    assert OutboundOrderItem.objects.get().document_total_price is None


def test_order_currency_must_be_supported(db, orders) -> None:
    with pytest.raises(WarehouseItemBadRequestError):
        orders.post("", json=_header(CustomerFactory(), document_currency="USD"))


def test_order_keeps_base_currency_it_was_created_with(db, orders) -> None:
    order = OutboundOrderFactory.it(currency="CZK")
    GlobalSettingsFactory(base_currency="EUR")

    data = orders.put(f"/{order.code}", json=_header(order.customer)).json()["data"]

    assert data["currency"] == "CZK"


def test_duplicate_order_keeps_frozen_currency_and_prices(db, orders) -> None:
    order = OutboundOrderFactory.it(
        document_currency="EUR", exchange_rate=Decimal("25")
    )
    OutboundOrderItemFactory.it(
        order=order,
        amount=Decimal("2"),
        unit_price=Decimal("50"),
        total_price=100,
        document_unit_price=Decimal("2"),
        document_total_price=Decimal("4"),
    )
    CurrencyRateFactory(currency="EUR", rate=Decimal("30"))

    data = orders.post(f"/{order.code}/duplicate").json()["data"]

    assert (data["document_currency"], data["exchange_rate"]) == ("EUR", 25)
    assert data["items"][0]["document_total_price"] == 4


# --- order items --- #


def _item(**extra) -> dict:
    return {
        "product_code": StockProductFactory().code,
        "product_name": "x",
        "amount": 4,
        **extra,
    }


def test_item_in_base_currency_mirrors_document_prices(db, orders) -> None:
    order = OutboundOrderFactory.it()

    item = orders.post(f"/{order.code}/items", json=_item(total_price=100)).json()[
        "data"
    ]

    assert item["unit_price"] == item["document_unit_price"] == 25
    assert item["total_price"] == item["document_total_price"] == 100
    assert OutboundOrderItem.objects.get().document_total_price is None


def test_item_in_foreign_currency_stores_exact_document_price(db, orders) -> None:
    order = OutboundOrderFactory.it(
        document_currency="EUR", exchange_rate=Decimal("24.33")
    )

    item = orders.post(
        f"/{order.code}/items", json=_item(document_total_price=10.5)
    ).json()["data"]

    assert item["document_total_price"] == 10.5
    assert item["document_unit_price"] == 2.625
    assert item["total_price"] == pytest.approx(255.465)
    assert item["unit_price"] == pytest.approx(63.8663)
    model = OutboundOrderItem.objects.get()
    assert model.document_total_price == Decimal("10.5")


def test_foreign_item_given_only_base_price_derives_document_price(db, orders) -> None:
    order = OutboundOrderFactory.it(
        document_currency="EUR", exchange_rate=Decimal("25")
    )

    item = orders.post(f"/{order.code}/items", json=_item(total_price=100)).json()[
        "data"
    ]

    assert (item["total_price"], item["document_total_price"]) == (100, 4)


def test_document_price_wins_over_base_price(db, orders) -> None:
    order = OutboundOrderFactory.it(
        document_currency="EUR", exchange_rate=Decimal("25")
    )

    item = orders.post(
        f"/{order.code}/items", json=_item(total_price=1, document_total_price=8)
    ).json()["data"]

    assert (item["total_price"], item["document_total_price"]) == (200, 8)


def test_item_requires_some_price(db, orders) -> None:
    order = OutboundOrderFactory.it()

    with pytest.raises(WarehouseItemBadRequestError):
        orders.post(f"/{order.code}/items", json=_item())


def test_document_price_is_rejected_for_base_currency_order(db, orders) -> None:
    order = OutboundOrderFactory.it()

    with pytest.raises(WarehouseItemBadRequestError):
        orders.post(f"/{order.code}/items", json=_item(document_total_price=5))


def test_minimum_item_value_is_applied_in_base_currency(db, orders) -> None:
    GlobalSettingsFactory(minimum_item_value=Decimal("100"))
    order = OutboundOrderFactory.it(
        document_currency="EUR", exchange_rate=Decimal("25")
    )

    item = orders.post(
        f"/{order.code}/items", json=_item(document_total_price=1)
    ).json()["data"]

    # 1 EUR = 25 CZK < 100 CZK minimum -> rounded up, 100 CZK = 4 EUR
    assert (item["total_price"], item["document_total_price"]) == (100, 4)


def test_update_item_reprices_with_the_frozen_rate(db, orders) -> None:
    order = OutboundOrderFactory.it(
        document_currency="EUR", exchange_rate=Decimal("25")
    )
    created = orders.post(
        f"/{order.code}/items", json=_item(document_total_price=4)
    ).json()["data"]
    CurrencyRateFactory(currency="EUR", rate=Decimal("99"))

    item = orders.put(
        f"/{order.code}/items/{created['index']}", json=_item(document_total_price=8)
    ).json()["data"]

    assert (item["document_total_price"], item["total_price"]) == (8, 200)


def test_pricing_details_stay_in_base_currency(db, orders) -> None:
    order = OutboundOrderFactory.it(
        document_currency="EUR", exchange_rate=Decimal("25")
    )

    item = orders.post(
        f"/{order.code}/items", json=_item(document_total_price=4)
    ).json()["data"]

    assert item["pricing_details"]["selected_unit_price"] == 25


# --- calculations --- #


def test_calculation_flows_into_order_with_frozen_currency(
    db, calculations, orders
) -> None:
    CurrencyRateFactory(currency="EUR", rate=Decimal("25"))
    customer = CustomerFactory(currency="EUR")
    created = calculations.post("", json=_header(customer)).json()["data"]
    assert created["document_currency"] == "EUR"
    calculations.post(f"/{created['code']}/items", json=_item(document_total_price=12))
    CurrencyRate.objects.update(rate=Decimal("40"))

    order = calculations.post(f"/{created['code']}/create-order").json()["data"]

    assert (order["document_currency"], order["exchange_rate"]) == ("EUR", 25)
    assert order["items"][0]["document_total_price"] == 12
    assert order["items"][0]["total_price"] == 300


def test_duplicate_calculation_keeps_currency(db, calculations) -> None:
    calculation = OutboundCalculationFactory.it(
        document_currency="EUR", exchange_rate=Decimal("25")
    )
    OutboundCalculationItemFactory.it(
        calculation=calculation,
        total_price=100,
        unit_price=100,
        amount=1,
        document_total_price=Decimal("4"),
        document_unit_price=Decimal("4"),
    )

    data = calculations.post(f"/{calculation.code}/duplicate").json()["data"]

    assert (data["document_currency"], data["exchange_rate"]) == ("EUR", 25)
    assert data["items"][0]["document_total_price"] == 4


# --- returns & invoices --- #


def test_return_credits_the_document_price(db) -> None:
    from apps.warehouse.models.orders import OutboundOrderState

    client = TestClient(order_routes.routes)
    order = OutboundOrderFactory.it(
        state=OutboundOrderState.SENT,
        document_currency="EUR",
        exchange_rate=Decimal("25"),
    )
    OutboundOrderItemFactory.it(
        order=order,
        amount=Decimal("10"),
        unit_price=Decimal("50"),
        total_price=500,
        document_unit_price=Decimal("2"),
        document_total_price=Decimal("20"),
    )

    data = client.post(
        f"/{order.code}/returns", json={"items": [{"item_index": 0, "amount": 3}]}
    ).json()["data"]

    returned = [i for i in data["items"] if i["is_returned"]][0]
    assert (returned["document_total_price"], returned["total_price"]) == (6, 150)
    assert returned["document_unit_price"] == 2


def _invoiceable(**kwargs) -> OutboundOrder:
    order = OutboundOrderFactory.it(**kwargs)
    OutboundOrderItemFactory.it(
        order=order,
        amount=Decimal("2"),
        unit_price=Decimal("50"),
        total_price=100,
        document_unit_price=Decimal("2") if order.document_currency != "CZK" else None,
        document_total_price=Decimal("4") if order.document_currency != "CZK" else None,
    )
    WarehouseOrderOutFactory(order=order, state=OutboundWarehouseOrderState.COMPLETED)
    return order


def _invoice_body(*orders: OutboundOrder) -> dict:
    CustomerFactory(is_self=True)
    return {
        "order_codes": [o.code for o in orders],
        "issued_date": "2026-11-01",
        "taxable_supply_date": "2026-11-01",
        "payment_method_name": InvoicePaymentMethodFactory.it(name="Cash").name,
    }


def test_invoice_is_issued_in_document_currency_with_document_prices(db) -> None:
    client = TestClient(invoice_routes.routes)
    order = _invoiceable(document_currency="EUR", exchange_rate=Decimal("25"))

    response = client.post("/outbound", json=_invoice_body(order))

    data = response.json()["data"]
    assert data["currency"] == "EUR"
    invoiced = data["outbound_orders"][0]
    assert invoiced["currency"] == "EUR"
    assert (
        invoiced["items"][0]["unit_price"],
        invoiced["items"][0]["total_price"],
    ) == (2, 4)


def test_invoice_of_base_currency_order_is_unchanged(db) -> None:
    client = TestClient(invoice_routes.routes)
    order = _invoiceable()

    data = client.post("/outbound", json=_invoice_body(order)).json()["data"]

    assert data["currency"] == "CZK"
    assert data["outbound_orders"][0]["items"][0]["total_price"] == 100


def test_cannot_invoice_orders_of_different_document_currencies_together(db) -> None:
    client = TestClient(invoice_routes.routes)
    customer = CustomerFactory()
    czk = _invoiceable(customer=customer)
    eur = _invoiceable(
        customer=customer, document_currency="EUR", exchange_rate=Decimal("25")
    )

    with pytest.raises(WarehouseItemBadRequestError, match="same currency"):
        client.post("/outbound", json=_invoice_body(czk, eur))
