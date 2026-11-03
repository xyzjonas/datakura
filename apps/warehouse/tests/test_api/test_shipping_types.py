import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.shipping_types import routes
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.models.shipping import UNKNOWN_SHIPPING_TYPE_ID, ShippingType
from apps.warehouse.tests.factories.order import (
    OutboundOrderFactory,
    OutboundOrderShippingFactory,
    ShippingTypeFactory,
)


def _user_types():
    # the sentinel is created by the migration
    return ShippingType.objects.exclude(pk=UNKNOWN_SHIPPING_TYPE_ID)


@pytest.mark.parametrize(
    ("search", "expected"),
    [
        ("ppl", ["Balík PPL"]),
        ("PPL", ["Balík PPL"]),
        ("í", ["Balík PPL", "Osobní odběr"]),
        ("", ["Balík PPL", "Osobní odběr"]),
        ("nothing", []),
    ],
)
def test_get_shipping_types_with_search(db, search: str, expected: list[str]) -> None:
    client = TestClient(routes)
    ShippingTypeFactory.it(name="Balík PPL")
    ShippingTypeFactory.it(name="Osobní odběr")

    res = client.get(f"/?search_term={search}")

    assert res.status_code == 200
    body = res.json()
    assert [item["name"] for item in body["data"]] == expected
    assert body["count"] == len(expected)


def test_get_shipping_types_paginated(db) -> None:
    client = TestClient(routes)
    for i in range(3):
        ShippingTypeFactory.it(name=f"Type {i}")

    res = client.get("/?page=2&page_size=2")

    body = res.json()
    assert [item["name"] for item in body["data"]] == ["Type 2"]
    assert body["count"] == 3
    assert body["previous"] == 1
    assert body["next"] is None


def test_create_shipping_type(db) -> None:
    client = TestClient(routes)

    res = client.post("/", json={"name": "  Balík PPL "})

    assert res.status_code == 200
    assert res.json()["data"]["name"] == "Balík PPL"
    assert _user_types().count() == 1


def test_create_shipping_type_is_idempotent(db) -> None:
    client = TestClient(routes)
    existing = ShippingTypeFactory.it(name="Balík PPL")

    res = client.post("/", json={"name": "Balík PPL"})

    assert res.json()["data"]["id"] == existing.id
    assert _user_types().count() == 1


def test_create_shipping_type_rejects_empty_name(db) -> None:
    client = TestClient(routes)

    res = client.post("/", json={"name": ""})

    assert res.status_code == 422
    assert not _user_types().exists()


def test_update_shipping_type(db) -> None:
    client = TestClient(routes)
    shipping_type = ShippingTypeFactory.it(name="PPL")

    res = client.put(f"/{shipping_type.id}", json={"name": "Balík PPL"})

    assert res.status_code == 200
    assert res.json()["data"]["name"] == "Balík PPL"


def test_update_missing_shipping_type_is_not_found(db) -> None:
    client = TestClient(routes)

    with pytest.raises(ShippingType.DoesNotExist):
        client.put("/999999", json={"name": "x"})


def test_delete_shipping_type(db) -> None:
    client = TestClient(routes)
    shipping_type = ShippingTypeFactory.it()

    res = client.delete(f"/{shipping_type.id}")

    assert res.status_code == 200
    assert res.json()["success"] is True
    assert not _user_types().exists()


def test_delete_shipping_type_in_use_is_rejected(db) -> None:
    client = TestClient(routes)
    shipping_type = ShippingTypeFactory.it()
    OutboundOrderShippingFactory.it(shipping_type=shipping_type)

    with pytest.raises(WarehouseItemBadRequestError, match="used by existing"):
        client.delete(f"/{shipping_type.id}")

    assert ShippingType.objects.filter(pk=shipping_type.pk).exists()


def test_unknown_sentinel_is_hidden_from_the_list(db) -> None:
    client = TestClient(routes)
    OutboundOrderFactory.it()  # its shipping uses the sentinel
    ShippingTypeFactory.it(name="Balík PPL")
    assert ShippingType.objects.filter(pk=UNKNOWN_SHIPPING_TYPE_ID).exists()

    body = client.get("/").json()

    assert [item["name"] for item in body["data"]] == ["Balík PPL"]
    assert body["count"] == 1


def test_unknown_sentinel_has_a_very_high_id(db) -> None:
    assert ShippingType.get_unknown() == UNKNOWN_SHIPPING_TYPE_ID == 2**31 - 1


def test_unknown_sentinel_is_created_once(db) -> None:
    ShippingType.get_unknown()
    ShippingType.get_unknown()

    assert ShippingType.objects.filter(pk=UNKNOWN_SHIPPING_TYPE_ID).count() == 1


@pytest.mark.parametrize("method", ["put", "delete"])
def test_unknown_sentinel_cannot_be_changed(db, method: str) -> None:
    client = TestClient(routes)
    ShippingType.get_unknown()
    kwargs = {"json": {"name": "Hacked"}} if method == "put" else {}

    with pytest.raises(WarehouseItemBadRequestError, match="cannot be changed"):
        getattr(client, method)(f"/{UNKNOWN_SHIPPING_TYPE_ID}", **kwargs)

    assert ShippingType.objects.get(pk=UNKNOWN_SHIPPING_TYPE_ID).name == "Neurčeno"


def test_unknown_name_is_reserved(db) -> None:
    client = TestClient(routes)

    with pytest.raises(WarehouseItemBadRequestError, match="reserved"):
        client.post("/", json={"name": "Neurčeno"})
