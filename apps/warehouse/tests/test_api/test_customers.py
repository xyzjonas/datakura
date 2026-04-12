from typing import cast

import pytest
from ninja.testing import TestClient

from apps.warehouse.core.schemas.customer import GetCustomersResponse
from apps.warehouse.models.customer import Customer
from apps.warehouse.tests.factories.product import PriceGroupFactory
from apps.warehouse.tests.factories.customer import CustomerFactoryWithContacts
from apps.warehouse.api.routes.customer import routes


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def test_get_all_customers(db, client) -> None:
    customer_model = cast(Customer, CustomerFactoryWithContacts())

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
def test_get_all_customers_active(db, client, flag) -> None:
    inactive = cast(Customer, CustomerFactoryWithContacts(is_valid=False))
    active = cast(Customer, CustomerFactoryWithContacts(is_valid=True))

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
def test_get_all_customers_deleted(db, client, flag) -> None:
    active = cast(Customer, CustomerFactoryWithContacts(is_deleted=False))
    deleted = cast(Customer, CustomerFactoryWithContacts(is_deleted=True))

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


@pytest.mark.parametrize(
    "attr", ["name", "code", "tax_identification", "identification"]
)
def test_get_all_customers_search_by_attribute(db, client, attr) -> None:
    CustomerFactoryWithContacts.create_batch(10)
    customer_model = cast(
        Customer, CustomerFactoryWithContacts(**{attr: "Test123456Customer"})
    )

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


def test_assign_customer_discount_group(db, client) -> None:
    customer = cast(Customer, CustomerFactoryWithContacts())
    discount_group = PriceGroupFactory(code="A", name="Group A", discount_percent=5)

    res = client.patch(
        f"/{customer.code}/discount-group",
        json={"discount_group_code": discount_group.code},
    )

    assert res.status_code == 200
    assert res.json()["data"]["discount_group"]["code"] == "A"
    assert res.json()["data"]["discount_group"]["discount_percent"] == 5.0


def test_unassign_customer_discount_group(db, client) -> None:
    discount_group = PriceGroupFactory(code="B", name="Group B", discount_percent=10)
    customer = cast(
        Customer, CustomerFactoryWithContacts(discount_group=discount_group)
    )

    res = client.patch(
        f"/{customer.code}/discount-group",
        json={"discount_group_code": None},
    )

    assert res.status_code == 200
    assert res.json()["data"]["discount_group"] is None
