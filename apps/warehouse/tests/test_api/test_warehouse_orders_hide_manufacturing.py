import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.warehouse import routes
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrderState,
    OutboundWarehouseOrderState,
)
from apps.warehouse.tests.factories.manufacturing import ManufacturingOrderFactory
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    WarehouseOrderOutFactory,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def _codes(res) -> set[str]:
    assert res.status_code == 200
    return {o["code"] for o in res.json()["data"]}


@pytest.fixture
def outbound(db):
    mfg = ManufacturingOrderFactory.it()
    regular = WarehouseOrderOutFactory.it(state=OutboundWarehouseOrderState.PENDING)
    linked = WarehouseOrderOutFactory.it(
        order=None,
        manufacturing_order=mfg,
        state=OutboundWarehouseOrderState.PENDING,
    )
    return regular, linked


@pytest.fixture
def inbound(db):
    mfg = ManufacturingOrderFactory.it()
    regular = InboundWarehouseOrderFactory.it(state=InboundWarehouseOrderState.PENDING)
    linked = InboundWarehouseOrderFactory.it(
        order=None,
        manufacturing_order=mfg,
        state=InboundWarehouseOrderState.PENDING,
    )
    return regular, linked


@pytest.mark.parametrize("query", ["", "?hide_manufacturing=false"])
def test_outbound_list_includes_manufacturing_by_default(client, outbound, query):
    regular, linked = outbound

    assert _codes(client.get(f"orders-outgoing{query}")) == {regular.code, linked.code}


def test_outbound_list_hides_manufacturing(client, outbound):
    regular, _ = outbound

    res = client.get("orders-outgoing?hide_manufacturing=true")

    assert _codes(res) == {regular.code}
    assert res.json()["count"] == 1


@pytest.mark.parametrize("query", ["", "?hide_manufacturing=false"])
def test_inbound_list_includes_manufacturing_by_default(client, inbound, query):
    regular, linked = inbound

    assert _codes(client.get(f"orders-incoming{query}")) == {regular.code, linked.code}


def test_inbound_list_hides_manufacturing(client, inbound):
    regular, _ = inbound

    res = client.get("orders-incoming?hide_manufacturing=true")

    assert _codes(res) == {regular.code}
    assert res.json()["count"] == 1


def test_hide_manufacturing_combines_with_search(client, outbound):
    regular, linked = outbound

    hidden = client.get(
        f"orders-outgoing?hide_manufacturing=true&search_term={linked.code}"
    )
    shown = client.get(f"orders-outgoing?search_term={linked.code}")

    assert _codes(hidden) == set()
    assert _codes(shown) == {linked.code}


def test_hide_manufacturing_with_include_all(client, outbound):
    regular, _ = outbound

    res = client.get("orders-outgoing?hide_manufacturing=true&include_all=true")

    assert _codes(res) == {regular.code}
