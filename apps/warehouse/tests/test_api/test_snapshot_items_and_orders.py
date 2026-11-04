from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal

import pytest
from django.core.exceptions import ObjectDoesNotExist
from ninja.testing import TestClient

from apps.warehouse.api.routes.analytics import routes
from apps.warehouse.core.services.inventory_snapshots import inventory_snapshot_service
from apps.warehouse.models.orders import InboundOrderState
from apps.warehouse.models.warehouse import OutboundWarehouseOrderState
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InboundOrderItemFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.warehouse import (
    OutboundWarehouseOrderItemFactory,
    WarehouseItemFactory,
    WarehouseLocationFactory,
    WarehouseOrderOutFactory,
)

T0 = datetime(2026, 1, 10, 12, 0, tzinfo=dt_timezone.utc)


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def make_items(count: int, *, prefix: str = "P") -> None:
    location = WarehouseLocationFactory(code=f"{prefix}-LOC")
    for i in range(count):
        product = StockProductFactory(
            code=f"{prefix}-{i:03d}", name=f"Name {prefix} {i:03d}"
        )
        WarehouseItemFactory(
            stock_product=product, amount=1, location=location, order_in=None
        )


def closed_inbound(*, closed_at, prices=(("10", "2"),), currency="CZK", state=None):
    order = InboundOrderFactory(
        currency=currency,
        state=state or InboundOrderState.COMPLETED,
        completed_date=closed_at,
        supplier=CustomerFactory(name="Dodavatel s.r.o."),
        description="Nákup profilů",
    )
    for amount, unit in prices:
        InboundOrderItemFactory(
            order=order, amount=Decimal(amount), unit_price=Decimal(unit)
        )
    return order


def closed_outbound(
    *, closed_at, shipment_prices=("100", "50"), currency="CZK", state=None
):
    base = OutboundOrderFactory(
        currency=currency,
        customer=CustomerFactory(name="Odběratel a.s."),
        description="Prodej",
        # base order total must be ignored in favour of the warehouse order's
    )
    w_order = WarehouseOrderOutFactory(
        order=base,
        state=state or OutboundWarehouseOrderState.COMPLETED,
        completed_date=closed_at,
    )
    for price in shipment_prices:
        OutboundWarehouseOrderItemFactory(
            warehouse_order=w_order,
            source_order_item=OutboundOrderItemFactory(order=base),
            price_at_shipment=Decimal(price),
        )
    return w_order


# --------------------------------------------------------------------------- items


@pytest.mark.parametrize(
    ("page", "page_size", "expected_len", "has_next", "has_prev"),
    [
        (1, 100, 5, False, False),
        (1, 2, 2, True, False),
        (2, 2, 2, True, True),
        (3, 2, 1, False, True),
        (4, 2, 0, False, True),  # beyond the last page
    ],
)
def test_items_endpoint_paginates(
    db, client, page, page_size, expected_len, has_next, has_prev
):
    make_items(5)
    snapshot = inventory_snapshot_service.create_snapshot()

    response = client.get(
        f"inventory-snapshots/{snapshot.id}/items",
        query_params={"page": page, "page_size": page_size},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 5
    assert len(payload["data"]) == expected_len
    assert (payload["next"] is not None) is has_next
    assert (payload["previous"] is not None) is has_prev


def test_items_endpoint_default_page_size_is_100(db, client):
    make_items(101)
    snapshot = inventory_snapshot_service.create_snapshot()

    payload = client.get(f"inventory-snapshots/{snapshot.id}/items").json()

    assert payload["count"] == 101
    assert len(payload["data"]) == 100
    assert payload["next"] == 2


def test_items_endpoint_clamps_page_size(db, client):
    make_items(3)
    snapshot = inventory_snapshot_service.create_snapshot()

    payload = client.get(
        f"inventory-snapshots/{snapshot.id}/items", query_params={"page_size": 100000}
    ).json()

    assert len(payload["data"]) == 3


def test_items_endpoint_is_sorted_by_product_code(db, client):
    make_items(3)
    snapshot = inventory_snapshot_service.create_snapshot()

    data = client.get(f"inventory-snapshots/{snapshot.id}/items").json()["data"]

    assert [row["product_code"] for row in data] == ["P-000", "P-001", "P-002"]


@pytest.mark.parametrize(
    ("search", "expected"),
    [
        ("P-001", ["P-001"]),
        ("p-001", ["P-001"]),  # case-insensitive
        ("name p 002", ["P-002"]),  # product name, case-insensitive
        ("Name P 002", ["P-002"]),
        ("Q-LOC", ["Q-000"]),  # location code
        ("  P-00  ", ["P-000", "P-001", "P-002"]),  # trimmed, partial
        ("", ["P-000", "P-001", "P-002", "Q-000"]),
        ("nothing-like-this", []),
    ],
)
def test_items_endpoint_search(db, client, search, expected):
    make_items(3, prefix="P")
    make_items(1, prefix="Q")
    snapshot = inventory_snapshot_service.create_snapshot()

    payload = client.get(
        f"inventory-snapshots/{snapshot.id}/items", query_params={"search": search}
    ).json()

    assert [row["product_code"] for row in payload["data"]] == expected
    assert payload["count"] == len(expected)


def test_items_endpoint_only_returns_lines_of_requested_snapshot(db, client):
    make_items(2)
    first = inventory_snapshot_service.create_snapshot()
    make_items(1, prefix="Z")
    second = inventory_snapshot_service.create_snapshot()

    assert client.get(f"inventory-snapshots/{first.id}/items").json()["count"] == 2
    assert client.get(f"inventory-snapshots/{second.id}/items").json()["count"] == 3


def test_items_queryset_unknown_snapshot_raises_not_found(db):
    # the API's ObjectDoesNotExist handler turns this into a 404
    with pytest.raises(ObjectDoesNotExist):
        inventory_snapshot_service.get_items_queryset(999999)


# -------------------------------------------------------------------------- orders


def test_first_snapshot_collects_all_closed_orders_with_totals(db, client):
    inbound = closed_inbound(closed_at=T0, prices=(("10", "2"), ("3", "5")))  # 35
    outbound = closed_outbound(closed_at=T0, shipment_prices=("100.50", "20"))  # 120.5

    snapshot = inventory_snapshot_service.create_snapshot(captured_at=T0)
    payload = client.get(f"inventory-snapshots/{snapshot.id}").json()["data"]

    assert payload["expenditure_totals"] == [{"currency": "CZK", "value": "35.0000"}]
    assert payload["gain_totals"] == [{"currency": "CZK", "value": "120.5000"}]

    [in_row] = payload["inbound_orders"]
    assert in_row["code"] == inbound.code
    assert in_row["counterparty_name"] == "Dodavatel s.r.o."
    assert in_row["description"] == "Nákup profilů"
    assert Decimal(in_row["total_value"]) == Decimal("35")

    [out_row] = payload["outbound_orders"]
    assert out_row["code"] == outbound.code
    assert out_row["base_order_code"] == outbound.order.code
    assert out_row["counterparty_name"] == "Odběratel a.s."
    assert Decimal(out_row["total_value"]) == Decimal("120.5")


def test_only_orders_closed_since_previous_snapshot_are_included(db, client):
    closed_inbound(closed_at=T0 - timedelta(days=1))
    closed_outbound(closed_at=T0 - timedelta(days=1))
    inventory_snapshot_service.create_snapshot(captured_at=T0)

    new_in = closed_inbound(closed_at=T0 + timedelta(hours=1), prices=(("1", "7"),))
    new_out = closed_outbound(closed_at=T0 + timedelta(hours=2), shipment_prices=("9",))
    closed_inbound(closed_at=T0 + timedelta(days=3))  # after the 2nd snapshot
    second = inventory_snapshot_service.create_snapshot(
        captured_at=T0 + timedelta(days=1)
    )

    payload = client.get(f"inventory-snapshots/{second.id}").json()["data"]

    assert [o["code"] for o in payload["inbound_orders"]] == [new_in.code]
    assert [o["code"] for o in payload["outbound_orders"]] == [new_out.code]
    assert payload["expenditure_totals"] == [{"currency": "CZK", "value": "7.0000"}]
    assert payload["gain_totals"] == [{"currency": "CZK", "value": "9.0000"}]


def test_order_closed_exactly_at_previous_capture_is_not_counted_twice(db, client):
    closed_inbound(closed_at=T0)
    first = inventory_snapshot_service.create_snapshot(captured_at=T0)
    second = inventory_snapshot_service.create_snapshot(
        captured_at=T0 + timedelta(days=1)
    )

    assert (
        len(
            client.get(f"inventory-snapshots/{first.id}").json()["data"][
                "inbound_orders"
            ]
        )
        == 1
    )
    assert (
        client.get(f"inventory-snapshots/{second.id}").json()["data"]["inbound_orders"]
        == []
    )


def test_unclosed_and_cancelled_orders_are_ignored(db, client):
    closed_inbound(closed_at=T0, state=InboundOrderState.CANCELLED)
    closed_inbound(closed_at=None, state=InboundOrderState.PUTAWAY)
    closed_outbound(closed_at=T0, state=OutboundWarehouseOrderState.CANCELLED)
    closed_outbound(closed_at=None, state=OutboundWarehouseOrderState.STARTED)

    snapshot = inventory_snapshot_service.create_snapshot(captured_at=T0)
    payload = client.get(f"inventory-snapshots/{snapshot.id}").json()["data"]

    assert payload["inbound_orders"] == []
    assert payload["outbound_orders"] == []
    assert payload["expenditure_totals"] == []
    assert payload["gain_totals"] == []


def test_totals_are_split_by_currency(db, client):
    closed_inbound(closed_at=T0, currency="CZK", prices=(("1", "10"),))
    closed_inbound(closed_at=T0, currency="EUR", prices=(("1", "4"),))
    closed_outbound(closed_at=T0, currency="EUR", shipment_prices=("6",))

    snapshot = inventory_snapshot_service.create_snapshot(captured_at=T0)
    payload = client.get(f"inventory-snapshots/{snapshot.id}").json()["data"]

    assert payload["expenditure_totals"] == [
        {"currency": "CZK", "value": "10.0000"},
        {"currency": "EUR", "value": "4.0000"},
    ]
    assert payload["gain_totals"] == [{"currency": "EUR", "value": "6.0000"}]


def test_order_without_priced_items_counts_as_zero(db, client):
    closed_inbound(closed_at=T0, prices=())
    closed_outbound(closed_at=T0, shipment_prices=())

    snapshot = inventory_snapshot_service.create_snapshot(captured_at=T0)
    payload = client.get(f"inventory-snapshots/{snapshot.id}").json()["data"]

    assert len(payload["inbound_orders"]) == 1
    assert Decimal(payload["inbound_orders"][0]["total_value"]) == 0
    assert len(payload["outbound_orders"]) == 1


def test_frozen_order_skeleton_survives_later_changes(db, client):
    order = closed_inbound(closed_at=T0, prices=(("2", "5"),))
    snapshot = inventory_snapshot_service.create_snapshot(captured_at=T0)

    order.items.update(total_price=Decimal("999"))
    order.supplier.name = "Renamed"
    order.supplier.save()
    order.description = "changed"
    order.save()

    [row] = client.get(f"inventory-snapshots/{snapshot.id}").json()["data"][
        "inbound_orders"
    ]
    assert Decimal(row["total_value"]) == Decimal("10")
    assert row["counterparty_name"] == "Dodavatel s.r.o."
    assert row["description"] == "Nákup profilů"


def test_period_start_is_previous_capture_and_none_for_first(db, client):
    first = inventory_snapshot_service.create_snapshot(captured_at=T0)
    second = inventory_snapshot_service.create_snapshot(
        captured_at=T0 + timedelta(days=1)
    )

    first_payload = client.get(f"inventory-snapshots/{first.id}").json()["data"]
    second_payload = client.get(f"inventory-snapshots/{second.id}").json()["data"]

    assert first_payload["period_start"] is None
    assert datetime.fromisoformat(second_payload["period_start"]) == T0


def test_period_start_stays_frozen_when_earlier_snapshot_is_added_later(db, client):
    first = inventory_snapshot_service.create_snapshot(captured_at=T0)
    second = inventory_snapshot_service.create_snapshot(
        captured_at=T0 + timedelta(days=2)
    )
    inventory_snapshot_service.create_snapshot(captured_at=T0 + timedelta(days=1))

    payload = client.get(f"inventory-snapshots/{second.id}").json()["data"]

    assert datetime.fromisoformat(payload["period_start"]) == T0
