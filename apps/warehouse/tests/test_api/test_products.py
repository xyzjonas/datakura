from typing import cast

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.product import routes
from apps.warehouse.api.schemas.product import ProductSchema, GetProductsResponse
from apps.warehouse.models.product import StockProduct

from apps.warehouse.tests.factories.product import (
    StockProductWithConversionsFactory,
    StockProductFactory,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def test_get_all_empty(db, client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.data == {
        "count": 0,
        "data": [],
        "message": None,
        "success": True,
        "next": None,
        "previous": None,
    }


def test_get_all_one_product(db, client):
    product = cast(StockProduct, StockProductWithConversionsFactory())
    response = client.get("/")
    assert response.status_code == 200
    assert (
        GetProductsResponse(**response.data).model_dump()
        == GetProductsResponse(
            **{
                "count": 1,
                "data": [
                    ProductSchema(
                        **{
                            "created": product.created,
                            "changed": product.changed,
                            "code": product.code,
                            "conversion_factors": [
                                {
                                    "factor": factor.conversion_factor,
                                    "unit_of_measure": factor.uom.name,
                                }
                                for factor in product.conversion_factors.all()
                            ],
                            "group": product.group.name,
                            "name": product.name,
                            "type": product.type.name,
                            "unit": product.base_uom.name,
                        }
                    ).model_dump()
                ],
                "message": None,
                "next": None,
                "previous": None,
                "success": True,
            }
        ).model_dump()
    )


def test_get_all_pagination(db, client):
    item_count = 200
    StockProductFactory.create_batch(item_count)

    response = client.get("/?page_size=10")
    assert response.status_code == 200
    response = GetProductsResponse(**response.data)
    assert response.success
    assert len(response.data) == 10
    assert response.count == item_count
    assert response.next == 2
    assert response.previous is None

    response = client.get("/?page_size=10&page=2")
    assert response.status_code == 200
    response = GetProductsResponse(**response.data)
    assert len(response.data) == 10
    assert response.count == item_count
    assert response.next == 3
    assert response.previous == 1

    response = client.get(f"/?page_size={item_count}")
    assert response.status_code == 200
    response = GetProductsResponse(**response.data)
    assert len(response.data) == item_count
    assert response.count == item_count
    assert response.next is None
    assert response.previous is None

    response = client.get(f"/?page_size={item_count}&page=2")
    assert response.status_code == 200
    response = GetProductsResponse(**response.data)
    assert len(response.data) == 0
    assert response.count == item_count
    assert response.next is None
    assert response.previous == 1


@pytest.mark.parametrize("attr", ["code", "name"])
def test_get_all_search(db, client, attr):
    item_count = 200
    StockProductFactory.create_batch(item_count)

    product = StockProduct.objects.first()

    response = client.get(f"?search_term={getattr(product, attr)}")
    assert response.status_code == 200
    response = GetProductsResponse(**response.data)
    assert response.success
    assert len(response.data) == 1
    assert response.count == 1
    assert response.next is None
    assert response.previous is None


@pytest.mark.parametrize("attr", ["code", "name"])
def test_get_all_search_partial(db, client, attr):
    item_count = 200
    StockProductFactory.create_batch(item_count)

    product = StockProduct.objects.first()

    response = client.get(f"?search_term={getattr(product, attr)[-5:]}")
    assert response.status_code == 200
    response = GetProductsResponse(**response.data)
    assert response.success
    found = [prod for prod in response.data if prod.code == product.code]
    assert len(found) == 1
