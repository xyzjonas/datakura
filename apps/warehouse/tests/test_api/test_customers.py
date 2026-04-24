from typing import cast

import pytest
from ninja.testing import TestClient

from apps.warehouse.core.schemas.customer import GetCustomersResponse
from apps.warehouse.models.customer import Customer
from apps.warehouse.tests.factories.product import PriceGroupFactory
from apps.warehouse.tests.factories.customer import CustomerFactoryWithContacts
from apps.warehouse.tests.factories.order import InvoicePaymentMethodFactory
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


def test_get_self_customer(db, client) -> None:
    self_customer = cast(Customer, CustomerFactoryWithContacts(is_self=True))

    res = client.get("/self")

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["code"] == self_customer.code
    assert data["is_self"] is True


def test_get_customers_filter_self_returns_paginated_single_item(db, client) -> None:
    self_customer = cast(Customer, CustomerFactoryWithContacts(is_self=True))
    CustomerFactoryWithContacts(is_self=False)

    res = client.get("/?is_self=true")

    assert res.status_code == 200
    response = GetCustomersResponse(**res.data)
    assert response.count == 1
    assert response.next is None
    assert response.previous is None
    assert len(response.data) == 1
    assert response.data[0].code == self_customer.code
    assert response.data[0].is_self is True


def test_get_customers_filter_self_returns_empty_array_when_missing(db, client) -> None:
    CustomerFactoryWithContacts(is_self=False)

    res = client.get("/?is_self=true")

    assert res.status_code == 200
    response = GetCustomersResponse(**res.data)
    assert response.count == 0
    assert response.next is None
    assert response.previous is None
    assert response.data == []


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


# ============ CRUD TESTS ============


def test_create_customer(db, client) -> None:
    """Test creating a new customer"""
    from apps.warehouse.tests.factories.customer import CustomerGroupFactory

    group = CustomerGroupFactory()
    payment_method = InvoicePaymentMethodFactory.it(name="Bank transfer")

    res = client.post(
        "/",
        json={
            "code": "NEWCUST001",
            "name": "New Customer Inc.",
            "customer_type": "FIRMA",
            "price_type": "FIRMY",
            "customer_group_code": group.code,
            "email": "contact@newcust.com",
            "phone": "+420123456789",
            "street": "Main St 123",
            "city": "Prague",
            "postal_code": "11000",
            "state": "CZ",
            "is_self": True,
            "default_payment_method_name": payment_method.name,
        },
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["code"] == "NEWCUST001"
    assert data["name"] == "New Customer Inc."
    assert data["customer_type"] == "FIRMA"
    assert data["group"]["code"] == group.code
    assert data["is_self"] is True
    assert data["default_payment_method"]["name"] == payment_method.name


def test_update_customer(db, client) -> None:
    """Test updating an existing customer"""
    customer = cast(Customer, CustomerFactoryWithContacts())
    payment_method = InvoicePaymentMethodFactory.it(name="Cash")

    res = client.put(
        f"/{customer.code}",
        json={
            "code": customer.code,
            "name": "Updated Customer Name",
            "customer_type": customer.customer_type,
            "price_type": customer.price_type,
            "customer_group_code": customer.customer_group.code,
            "email": "newemail@example.com",
            "phone": "+999999999",
            "is_self": True,
            "default_payment_method_name": payment_method.name,
        },
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["name"] == "Updated Customer Name"
    assert data["email"] == "newemail@example.com"
    assert data["phone"] == "+999999999"
    assert data["is_self"] is True
    assert data["default_payment_method"]["name"] == payment_method.name


def test_delete_customer_soft_delete(db, client) -> None:
    """Test deleting a customer (soft delete)"""
    customer = cast(Customer, CustomerFactoryWithContacts())

    res = client.delete(f"/{customer.code}")

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["is_deleted"] is True

    # Verify in DB
    customer.refresh_from_db()
    assert customer.is_deleted is True


def test_create_contact_person(db, client) -> None:
    """Test creating a new contact person"""
    customer = cast(Customer, CustomerFactoryWithContacts())

    res = client.post(
        f"/{customer.code}/contacts",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "+420123456789",
            "title_pre": "Ing.",
            "birth_date": "1990-01-15",
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["email"] == "john@example.com"


def test_create_contact_person_minimal(db, client) -> None:
    """Test creating contact person with minimal required fields"""
    customer = cast(Customer, CustomerFactoryWithContacts())

    res = client.post(
        f"/{customer.code}/contacts",
        json={
            "first_name": "Jane",
            "last_name": "Smith",
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Smith"


def test_update_contact_person(db, client) -> None:
    """Test updating an existing contact person"""

    customer = cast(Customer, CustomerFactoryWithContacts())
    contact = customer.contacts.first()
    assert contact is not None

    res = client.put(
        f"/{customer.code}/contacts/{contact.id}",
        json={
            "first_name": contact.first_name,
            "last_name": "UpdatedLastName",
            "email": "updated@example.com",
            "phone": contact.phone,
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["last_name"] == "UpdatedLastName"
    assert data["email"] == "updated@example.com"


def test_delete_contact_person_soft_delete(db, client) -> None:
    """Test deleting a contact person (soft delete)"""
    customer = cast(Customer, CustomerFactoryWithContacts())
    contact = customer.contacts.first()
    assert contact is not None
    contact_id = contact.id

    res = client.delete(f"/{customer.code}/contacts/{contact_id}")

    assert res.status_code == 200
    data = res.json()
    assert data["is_deleted"] is True

    # Verify in DB
    contact.refresh_from_db()
    assert contact.is_deleted is True


def test_get_customer_contacts(db, client) -> None:
    """Test getting all contact persons for a customer"""
    customer = cast(Customer, CustomerFactoryWithContacts())

    res = client.get(f"/{customer.code}/contacts")

    assert res.status_code == 200
    contacts = res.json()
    assert len(contacts) == 2  # CustomerFactoryWithContacts creates 2 contacts
    assert all(not c["is_deleted"] for c in contacts)


def test_contact_fields_validation(db, client) -> None:
    """Test that contact creation validates required fields"""
    customer = cast(Customer, CustomerFactoryWithContacts())

    # Missing required first_name
    res = client.post(
        f"/{customer.code}/contacts",
        json={
            "last_name": "Doe",
        },
    )

    assert res.status_code != 200
