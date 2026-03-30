from typing import cast

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.group import routes
from apps.warehouse.core.schemas.group import GetProductGroupsResponse
from apps.warehouse.models.product import ProductGroup
from apps.warehouse.tests.factories.product import ProductGroupFactory


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def test_get_all_empty(db, client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.data == {
        "count": 0,
        "data": [],
        "error": None,
        "success": True,
        "next": None,
        "previous": None,
    }


def test_get_all_groups(db, client):
    group = cast(ProductGroup, ProductGroupFactory(name="Electronics"))

    response = client.get("/")
    assert response.status_code == 200

    parsed = GetProductGroupsResponse(**response.data)
    assert parsed.count == 1
    assert parsed.next is None
    assert parsed.previous is None
    assert len(parsed.data) == 1
    assert parsed.data[0].name == group.name


def test_get_all_groups_pagination(db, client):
    item_count = 120
    ProductGroupFactory.create_batch(item_count)

    response = client.get("/?page_size=10")
    assert response.status_code == 200
    parsed = GetProductGroupsResponse(**response.data)
    assert len(parsed.data) == 10
    assert parsed.count == item_count
    assert parsed.next == 2
    assert parsed.previous is None

    response = client.get("/?page_size=10&page=2")
    assert response.status_code == 200
    parsed = GetProductGroupsResponse(**response.data)
    assert len(parsed.data) == 10
    assert parsed.count == item_count
    assert parsed.next == 3
    assert parsed.previous == 1


@pytest.mark.parametrize("search_term", ["electronics", "ELECTRONICS", "EleCtRoNiCs"])
def test_get_all_groups_search_case_insensitive(db, client, search_term):
    ProductGroupFactory.create_batch(20)
    ProductGroupFactory(name="Electronics")

    response = client.get(f"/?search_term={search_term}")
    assert response.status_code == 200
    parsed = GetProductGroupsResponse(**response.data)
    assert parsed.count == 1
    assert len(parsed.data) == 1
    assert parsed.data[0].name == "Electronics"


def test_create_group(db, client):
    response = client.post("/", json={"name": "New Group"})

    assert response.status_code == 200
    created = ProductGroup.objects.get(name="New Group")
    assert response.data["data"]["name"] == "New Group"
    assert created.name == "New Group"


def test_update_group(db, client):
    group = cast(ProductGroup, ProductGroupFactory(name="Old Group"))

    response = client.put(f"/{group.name}", json={"name": "Updated Group"})

    assert response.status_code == 200
    group.refresh_from_db()
    assert group.name == "Updated Group"
    assert response.data["data"]["name"] == "Updated Group"
