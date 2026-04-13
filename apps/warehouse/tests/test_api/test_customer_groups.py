from typing import cast

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.customer_groups import routes
from apps.warehouse.core.schemas.customer import GetCustomerGroupsResponse
from apps.warehouse.models.customer import CustomerGroup
from apps.warehouse.tests.factories.customer import CustomerGroupFactory


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


def test_get_all_customer_groups(db, client):
    group = cast(CustomerGroup, CustomerGroupFactory(name="Retail", code="RET"))

    response = client.get("/")
    assert response.status_code == 200

    parsed = GetCustomerGroupsResponse(**response.data)
    assert parsed.count == 1
    assert parsed.next is None
    assert parsed.previous is None
    assert len(parsed.data) == 1
    assert parsed.data[0].name == group.name
    assert parsed.data[0].code == group.code


def test_get_all_customer_groups_pagination(db, client):
    item_count = 50
    CustomerGroupFactory.create_batch(item_count)

    response = client.get("/?page_size=10")
    assert response.status_code == 200
    parsed = GetCustomerGroupsResponse(**response.data)
    assert len(parsed.data) == 10
    assert parsed.count == item_count
    assert parsed.next == 2
    assert parsed.previous is None


@pytest.mark.parametrize("search_term", ["ret", "RET", "ReT"])
def test_get_all_customer_groups_search_case_insensitive(db, client, search_term):
    CustomerGroupFactory.create_batch(10, name="Wholesale")
    CustomerGroupFactory(name="Retail", code="RET")

    response = client.get(f"/?search_term={search_term}")
    assert response.status_code == 200
    parsed = GetCustomerGroupsResponse(**response.data)
    assert parsed.count >= 1
    assert any(group.name == "Retail" for group in parsed.data)


def test_create_customer_group(db, client):
    response = client.post("/", json={"code": "ECO", "name": "E-commerce"})

    assert response.status_code == 200
    created = CustomerGroup.objects.get(code="ECO")
    assert response.data["data"]["code"] == "ECO"
    assert response.data["data"]["name"] == "E-commerce"
    assert created.name == "E-commerce"


def test_update_customer_group(db, client):
    group = cast(CustomerGroup, CustomerGroupFactory(name="Old", code="OLD"))

    response = client.put(f"/{group.code}", json={"code": "NEW", "name": "Updated"})

    assert response.status_code == 200
    group.refresh_from_db()
    assert group.code == "NEW"
    assert group.name == "Updated"
    assert response.data["data"]["code"] == "NEW"


def test_delete_customer_group(db, client):
    group = cast(CustomerGroup, CustomerGroupFactory(name="Delete Me", code="DEL"))

    response = client.delete(f"/{group.code}")

    assert response.status_code == 200
    assert response.data["data"]["code"] == "DEL"
    assert not CustomerGroup.objects.filter(code="DEL").exists()
