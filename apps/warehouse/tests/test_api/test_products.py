from typing import cast
from datetime import timedelta

import pytest
from django.utils import timezone
from ninja.testing import TestClient

from apps.warehouse.api.routes.product import routes
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.schemas.product import ProductSchema, GetProductsResponse
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction, AuditLog
from apps.warehouse.models.barcode import Barcode
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.product import PriceGroup
from apps.warehouse.models.product import StockProductPrice
from apps.warehouse.models.packaging import UnitOfMeasure

from apps.warehouse.tests.factories.product import StockProductFactory
from apps.warehouse.tests.factories.product import (
    PriceGroupFactory,
    StockProductPriceFactory,
    StockProductPriceCustomerFactory,
)
from apps.warehouse.tests.factories.customer import CustomerFactory


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
    assert product is not None

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


def test_create_product(db, client):
    response = client.post(
        "/",
        json={
            "name": "Test Product",
            "code": "PRD-NEW-001",
            "type": "Finished Good",
            "unit": "KS",
            "group": "Main Group",
            "unit_weight": 123.45,
            "base_price": 100,
            "purchase_price": 80,
            "currency": "CZK",
            "customs_declaration_group": "ABC123",
            "attributes": {"color": "blue"},
        },
    )

    assert response.status_code == 200
    product = StockProduct.objects.get(code="PRD-NEW-001")
    assert product.name == "Test Product"
    assert product.type.name == "Finished Good"
    assert product.group.name == "Main Group"
    assert product.unit_of_measure.name == "KS"
    assert float(product.unit_weight) == 123.45
    assert float(product.base_price) == 100
    assert float(product.purchase_price) == 80
    assert product.currency == "CZK"
    assert product.customs_declaration_group == "ABC123"
    assert product.attributes == {"color": "blue"}


def test_update_product(db, client):
    product = cast(StockProduct, StockProductFactory(code="PRD-UPDATE-001"))
    UnitOfMeasure.objects.get_or_create(name="kg")

    response = client.put(
        f"/{product.code}",
        json={
            "name": "Updated Product",
            "code": "PRD-UPDATE-002",
            "type": "Raw Material",
            "unit": "kg",
            "group": "Updated Group",
            "unit_weight": 12,
            "base_price": 110,
            "purchase_price": 90,
            "currency": "CZK",
            "customs_declaration_group": "DEF456",
            "attributes": {"size": "L"},
        },
    )

    assert response.status_code == 200
    product.refresh_from_db()
    assert product.code == "PRD-UPDATE-002"
    assert product.name == "Updated Product"
    assert product.type.name == "Raw Material"
    assert product.group.name == "Updated Group"
    assert product.unit_of_measure.name == "kg"
    assert float(product.base_price) == 110
    assert float(product.purchase_price) == 90
    assert product.customs_declaration_group == "DEF456"
    assert product.attributes == {"size": "L"}


def test_duplicate_product(db, client):
    source = cast(StockProduct, StockProductFactory(code="PRD-SOURCE-001"))

    response = client.post(
        f"/{source.code}/duplicate",
        json={
            "name": "Duplicated Product",
            "code": "PRD-DUP-001",
            "type": source.type.name,
            "unit": source.unit_of_measure.name,
            "group": source.group.name if source.group else None,
            "unit_weight": float(source.unit_weight),
            "base_price": float(source.base_price),
            "purchase_price": float(source.purchase_price),
            "currency": source.currency,
            "customs_declaration_group": source.customs_declaration_group,
            "attributes": source.attributes,
        },
    )

    assert response.status_code == 200
    duplicated = StockProduct.objects.get(code="PRD-DUP-001")
    assert duplicated.pk != source.pk
    assert duplicated.name == "Duplicated Product"
    assert duplicated.type.name == source.type.name
    assert duplicated.unit_of_measure.name == source.unit_of_measure.name


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
        reason=AuditMessages.PRODUCT_CREATED.CS,
    )
    newer_log = audit_service.add_entry(
        product,
        action=AuditAction.UPDATE,
        reason=AuditMessages.PRODUCT_UPDATED.CS,
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


def test_get_product_returns_dynamic_prices(db, client):
    product = cast(StockProduct, StockProductFactory())
    customer_for_override = CustomerFactory()
    StockProductPriceFactory(
        product=product,
        customer=customer_for_override,
        discount_percent=5,
    )
    customer_price = StockProductPriceCustomerFactory(
        product=product, discount_percent=10
    )

    response = client.get(f"/{product.code}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["dynamic_prices"]) == 2
    codes = {item["customer"]["code"] for item in data["dynamic_prices"]}
    assert customer_price.customer.code in codes
    assert customer_for_override.code in codes


def test_add_customer_dynamic_price(db, client):
    product = cast(StockProduct, StockProductFactory())
    customer = CustomerFactory()

    response = client.post(
        f"/{product.code}/prices",
        json={
            "discount_percent": 12,
            "customer_code": customer.code,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    added = next(
        item
        for item in data["dynamic_prices"]
        if item["customer"]["code"] == customer.code
    )
    assert added["customer"]["code"] == customer.code
    assert added["customer"]["name"] == customer.name


def test_update_dynamic_price(db, client):
    product = cast(StockProduct, StockProductFactory())
    price = StockProductPriceFactory(product=product, discount_percent=5)

    response = client.patch(
        f"/{product.code}/prices/{price.id}",
        json={
            "discount_percent": 15,
        },
    )

    assert response.status_code == 200
    price.refresh_from_db()
    assert float(price.discount_percent) == 15


def test_delete_dynamic_price(db, client):
    product = cast(StockProduct, StockProductFactory())
    price = StockProductPriceFactory(product=product, discount_percent=5)

    response = client.delete(f"/{product.code}/prices/{price.id}")

    assert response.status_code == 200
    assert StockProductPrice.objects.filter(id=price.id).exists() is False


@pytest.mark.parametrize(
    (
        "discount_mode",
        "discount_percent",
        "expected_source",
        "expected_reason_fragment",
    ),
    [
        ("customer", 15, "CUSTOMER_OVERRIDE", "Customer override"),
        ("group", 10, "CUSTOMER_GROUP", "Discount group"),
        ("none", 0, "BASE_PRICE", "Base selling price"),
    ],
)
def test_get_product_selling_price_lookup(
    db,
    client,
    discount_mode: str,
    discount_percent: int,
    expected_source: str,
    expected_reason_fragment: str,
):
    product = cast(StockProduct, StockProductFactory(base_price=200))
    customer = cast(Customer, CustomerFactory())

    if discount_mode == "customer":
        StockProductPriceCustomerFactory(
            product=product,
            customer=customer,
            discount_percent=discount_percent,
        )
    elif discount_mode == "group":
        customer.discount_group = cast(
            PriceGroup,
            PriceGroupFactory(
                code="GROUP-LKP",
                name="Lookup Group",
                discount_percent=discount_percent,
            ),
        )
        customer.save(update_fields=["discount_group", "changed"])

    response = client.get(
        f"/{product.code}/selling-price?customer_code={customer.code}"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["product_code"] == product.code
    assert data["customer_code"] == customer.code
    assert data["base_price"] == 200.0
    assert data["source"] == expected_source
    assert expected_reason_fragment in data["reason"]

    expected_price = round(200 * (1 - discount_percent / 100), 2)
    assert data["final_price"] == expected_price


def test_discount_group_crud(db, client):
    create_response = client.post(
        "/pricing/discount-groups/D",
        json={
            "name": "Group D",
            "discount_percent": 17,
            "is_active": True,
        },
    )

    assert create_response.status_code == 200
    assert create_response.json()["data"]["code"] == "D"
    assert create_response.json()["data"]["discount_percent"] == 17.0

    update_response = client.patch(
        "/pricing/discount-groups/D",
        json={
            "name": "Group D Premium",
            "discount_percent": 18,
            "is_active": False,
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["data"]["name"] == "Group D Premium"
    assert update_response.json()["data"]["discount_percent"] == 18.0
    assert update_response.json()["data"]["is_active"] is False

    list_response = client.get("/pricing/discount-groups")
    assert list_response.status_code == 200
    assert any(group["code"] == "D" for group in list_response.json()["data"])

    delete_response = client.delete("/pricing/discount-groups/D")
    assert delete_response.status_code == 200
    assert all(group["code"] != "D" for group in delete_response.json()["data"])
