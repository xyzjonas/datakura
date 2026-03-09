from typing import cast
from datetime import timedelta

import pytest
from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.product import routes
from apps.warehouse.core.schemas.product import ProductSchema, GetProductsResponse
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.models.barcode import Barcode
from apps.warehouse.models.product import StockProduct

from apps.warehouse.tests.factories.product import StockProductFactory


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


def test_get_all_one_product(db, client):
    product = cast(StockProduct, StockProductFactory())
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
                            "group": product.group.name,
                            "name": product.name,
                            "type": product.type.name,
                            "unit": product.unit_of_measure.name,
                            "unit_weight": product.unit_weight,
                            "base_price": product.base_price,
                            "purchase_price": product.purchase_price,
                            "currency": product.currency,
                            "attributes": product.attributes,
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


def test_add_product_barcode(db, client):
    product = cast(StockProduct, StockProductFactory())

    response = client.post(
        f"/{product.code}/barcodes",
        json={"code": "1234567890123", "is_primary": True},
    )

    assert response.status_code == 200
    barcode = Barcode.objects.get(code="1234567890123")
    assert barcode.is_primary is True
    assert barcode.content_object == product


def test_add_product_barcode_switches_primary(db, client):
    product = cast(StockProduct, StockProductFactory())
    product.attach_barcode(code="1111111111111", is_primary=True)

    response = client.post(
        f"/{product.code}/barcodes",
        json={"code": "2222222222222", "is_primary": True},
    )

    assert response.status_code == 200
    old_barcode = Barcode.objects.get(code="1111111111111")
    new_barcode = Barcode.objects.get(code="2222222222222")
    assert old_barcode.is_primary is False
    assert new_barcode.is_primary is True


def test_get_product_audits(db, client) -> None:
    product = cast(StockProduct, StockProductFactory())

    older_log = audit_service.add_entry(
        product,
        action=AuditAction.CREATE,
        reason="Product created",
    )
    newer_log = audit_service.add_entry(
        product,
        action=AuditAction.UPDATE,
        reason="Product updated",
    )

    now = timezone.now()
    AuditLog.objects.filter(pk=older_log.pk).update(created=now - timedelta(minutes=10))  # type: ignore
    AuditLog.objects.filter(pk=newer_log.pk).update(created=now)  # type: ignore

    res = client.get(f"/{product.code}/audits")

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 2
    assert data[0]["source"] == "audit"
    assert data[0]["action"] == AuditAction.UPDATE
    assert data[1]["action"] == AuditAction.CREATE
