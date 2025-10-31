import pytest
from ninja.testing import TestClient

from apps.warehouse.api.schemas.customer import GetCustomersResponse
from apps.warehouse.models.customer import Customer
from apps.warehouse.tests.factories.customer import CustomerFactoryWithContacts
from apps.warehouse.api.routes.customer import routes


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def test_get_all_customers(db, client):
    customer_model: Customer = CustomerFactoryWithContacts()

    res = client.get("/")
    assert res.status_code == 200
    response = GetCustomersResponse(**res.data)
    assert response.count == 1
    assert response.next is None
    assert response.previous is None
    assert len(response.data) == 1

    customer = response.data[0]
    assert customer.name == customer_model.name
    assert customer.customer_type == customer_model.customer_type
    assert customer.code == customer_model.code


@pytest.mark.parametrize("flag", ["false", "False", "0"])
def test_get_all_customers_active(db, client, flag):
    inactive: Customer = CustomerFactoryWithContacts(is_valid=False)
    active: Customer = CustomerFactoryWithContacts(is_valid=True)

    res = client.get("/")
    assert res.status_code == 200
    response = GetCustomersResponse(**res.data)
    assert response.count == 1
    assert response.next is None
    assert response.previous is None
    assert len(response.data) == 1

    customer = response.data[0]
    assert customer.name == active.name
    assert customer.customer_type == active.customer_type
    assert customer.code == active.code

    res = client.get(f"/?is_active={flag}")
    assert res.status_code == 200
    response = GetCustomersResponse(**res.data)
    assert response.count == 1
    assert response.next is None
    assert response.previous is None
    assert len(response.data) == 1

    customer = response.data[0]
    assert customer.name == inactive.name
    assert customer.customer_type == inactive.customer_type
    assert customer.code == inactive.code


@pytest.mark.parametrize("flag", ["true", "True", "1"])
def test_get_all_customers_deleted(db, client, flag):
    active: Customer = CustomerFactoryWithContacts(is_deleted=False)
    deleted: Customer = CustomerFactoryWithContacts(is_deleted=True)

    res = client.get("/")
    assert res.status_code == 200
    response = GetCustomersResponse(**res.data)
    assert response.count == 1
    assert response.next is None
    assert response.previous is None
    assert len(response.data) == 1

    customer = response.data[0]
    assert customer.name == active.name
    assert customer.customer_type == active.customer_type
    assert customer.code == active.code

    res = client.get(f"/?is_deleted={flag}")
    assert res.status_code == 200
    response = GetCustomersResponse(**res.data)
    assert response.count == 1
    assert response.next is None
    assert response.previous is None
    assert len(response.data) == 1

    customer = response.data[0]
    assert customer.name == deleted.name
    assert customer.customer_type == deleted.customer_type
    assert customer.code == deleted.code


def test_get_all_customers_search_by_code(db, client):
    CustomerFactoryWithContacts.create_batch(10)
    customer_model: Customer = CustomerFactoryWithContacts()

    res = client.get(f"/?search_term={customer_model.code}")
    assert res.status_code == 200
    response = GetCustomersResponse(**res.data)
    assert response.count == 1
    assert response.next is None
    assert response.previous is None
    assert len(response.data) == 1

    customer = response.data[0]
    assert customer.name == customer_model.name
    assert customer.customer_type == customer_model.customer_type
    assert customer.code == customer_model.code


def test_get_all_customers_search_by_name(db, client):
    CustomerFactoryWithContacts.create_batch(10)
    customer_model: Customer = CustomerFactoryWithContacts(name="Test123456Customer")

    res = client.get("/?search_term=123456")
    assert res.status_code == 200
    response = GetCustomersResponse(**res.data)
    assert response.count == 1
    assert response.next is None
    assert response.previous is None
    assert len(response.data) == 1

    customer = response.data[0]
    assert customer.name == customer_model.name
    assert customer.customer_type == customer_model.customer_type
    assert customer.code == customer_model.code
