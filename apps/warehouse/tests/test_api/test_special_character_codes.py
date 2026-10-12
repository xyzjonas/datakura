from urllib.parse import quote

import pytest
from django.test import Client

from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.product import StockProductFactory

CODES = [
    "AB/12",
    "/leading",
    "trailing/",
    "a//b",
    "A B",
    "A%B",
    "100%",
    "%2F",
    "A?B",
    "A#B",
    "A+B",
    "A&B",
    "A.B",
    "Ž-ŠČ/1",
]


def double_encode(code: str) -> str:
    """what the frontend does with every API path parameter"""
    return quote(quote(code, safe=""), safe="")


@pytest.fixture
def api(db, user) -> Client:
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.parametrize("code", CODES)
def test_get_product_by_special_code(api, code):
    StockProductFactory(code=code)

    response = api.get(f"/api/v1/products/{double_encode(code)}")

    assert response.status_code == 200
    assert response.json()["data"]["code"] == code


@pytest.mark.parametrize("code", CODES)
def test_get_customer_by_special_code(api, code):
    CustomerFactory(code=code)

    response = api.get(f"/api/v1/customers/{double_encode(code)}")

    assert response.status_code == 200
    assert response.json()["data"]["code"] == code


def test_nested_route_with_special_code(api):
    StockProductFactory(code="AB/12")

    response = api.get(f"/api/v1/products/{double_encode('AB/12')}/audits")

    assert response.status_code == 200


def test_single_encoded_plain_code_still_works(api):
    StockProductFactory(code="PLAIN-1")

    response = api.get("/api/v1/products/PLAIN-1")

    assert response.status_code == 200
    assert response.json()["data"]["code"] == "PLAIN-1"
