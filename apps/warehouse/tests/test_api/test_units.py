from typing import cast

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.packaging import routes
from apps.warehouse.core.schemas.packaging import GetUnitOfMeasuresResponse
from apps.warehouse.models.packaging import UnitOfMeasure
from apps.warehouse.tests.factories.units import UnitOfMeasureFactory


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def test_get_all_units_empty(db, client):
    response = client.get("/units")

    assert response.status_code == 200
    assert response.data == {
        "count": 0,
        "data": [],
        "error": None,
        "success": True,
        "next": None,
        "previous": None,
    }


def test_get_all_units(db, client):
    base = cast(UnitOfMeasure, UnitOfMeasureFactory(name="KS"))
    unit = cast(
        UnitOfMeasure,
        UnitOfMeasure.objects.create(
            name="BOX",
            amount_of_base_uom=10,
            base_uom=base,
        ),
    )

    response = client.get("/units")
    assert response.status_code == 200

    parsed = GetUnitOfMeasuresResponse(**response.data)
    assert parsed.count == 2
    assert len(parsed.data) == 2
    found = [item for item in parsed.data if item.name == unit.name][0]
    assert found.amount_of_base_uom == 10
    assert found.base_uom == "KS"


def test_get_all_units_pagination(db, client):
    UnitOfMeasure.objects.bulk_create(
        [
            UnitOfMeasure(name=f"UOM-{index}", amount_of_base_uom=1)
            for index in range(120)
        ]
    )

    response = client.get("/units?page_size=10")
    assert response.status_code == 200
    parsed = GetUnitOfMeasuresResponse(**response.data)
    assert parsed.count == 120
    assert len(parsed.data) == 10
    assert parsed.next == 2
    assert parsed.previous is None


@pytest.mark.parametrize("search_term", ["kg", "KG", "kG"])
def test_get_all_units_search_case_insensitive(db, client, search_term):
    UnitOfMeasureFactory.create_batch(10)
    UnitOfMeasureFactory(name="kg")

    response = client.get(f"/units?search_term={search_term}")

    assert response.status_code == 200
    parsed = GetUnitOfMeasuresResponse(**response.data)
    assert parsed.count == 1
    assert len(parsed.data) == 1
    assert parsed.data[0].name == "kg"


def test_create_unit(db, client):
    UnitOfMeasure.objects.create(name="ml", amount_of_base_uom=1)
    response = client.post(
        "/units",
        json={
            "name": "l",
            "amount_of_base_uom": 1000,
            "base_uom": "ml",
        },
    )

    assert response.status_code == 200
    assert response.data["data"]["name"] == "l"
    assert response.data["data"]["amount_of_base_uom"] == 1000
    assert response.data["data"]["base_uom"] == "ml"
    created = UnitOfMeasure.objects.get(name="l")
    assert float(created.amount_of_base_uom) == 1000
    assert created.base_uom is not None
    assert created.base_uom.name == "ml"


def test_update_unit(db, client):
    base = UnitOfMeasure.objects.create(name="BASE", amount_of_base_uom=1)
    unit = UnitOfMeasure.objects.create(name="old-uom", amount_of_base_uom=1)

    response = client.put(
        f"/units/{unit.name}",
        json={
            "name": "new-uom",
            "amount_of_base_uom": 25,
            "base_uom": "BASE",
        },
    )

    assert response.status_code == 200
    unit.refresh_from_db()
    assert unit.name == "new-uom"
    assert float(unit.amount_of_base_uom) == 25
    assert unit.base_uom is not None
    assert unit.base_uom.name == base.name
    assert response.data["data"]["name"] == "new-uom"
    assert response.data["data"]["amount_of_base_uom"] == 25
    assert response.data["data"]["base_uom"] == "BASE"
