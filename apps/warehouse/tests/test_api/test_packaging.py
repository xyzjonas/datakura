import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.packaging import routes
from apps.warehouse.core.exceptions import ApiBaseException, ErrorCode
from apps.warehouse.models.packaging import PackageType, UnitOfMeasure
from apps.warehouse.models.warehouse import TrackingLevel
from apps.warehouse.tests.factories.packaging import PackageTypeFactory
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    InboundWarehouseOrderItemFactory,
    WarehouseLocationFactory,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def test_get_package_types_with_search(db, client) -> None:
    matching_unit = UnitOfMeasure.objects.create(name="kg", amount_of_base_uom=1000)
    PackageType.objects.create(
        name="BOX-KG",
        description="Heavy goods",
        unit_of_measure=matching_unit,
        amount=10,
    )
    PackageType.objects.create(name="PALLET", description="Bulk transport", amount=100)

    res = client.get("/?search_term=heavy")

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == "BOX-KG"
    assert data[0]["unit"] == "kg"


def test_create_package_type(db, client) -> None:
    UnitOfMeasure.objects.create(name="KS", amount_of_base_uom=1)

    res = client.post(
        "/",
        json={
            "name": "BOX-10",
            "description": "Ten pieces box",
            "amount": 10,
            "unit": "KS",
        },
    )

    assert res.status_code == 200
    assert res.json()["data"]["name"] == "BOX-10"
    assert res.json()["data"]["description"] == "Ten pieces box"
    assert res.json()["data"]["amount"] == 10.0
    assert res.json()["data"]["unit"] == "KS"


def test_update_package_type(db, client) -> None:
    old_unit = UnitOfMeasure.objects.create(name="KS", amount_of_base_uom=1)
    new_unit = UnitOfMeasure.objects.create(name="BAL", amount_of_base_uom=1)
    package_type = PackageType.objects.create(
        name="BOX-OLD",
        description="Old desc",
        amount=10,
        unit_of_measure=old_unit,
    )

    res = client.put(
        f"/{package_type.name}",
        json={
            "name": "BOX-NEW",
            "description": "New desc",
            "amount": 12,
            "unit": new_unit.name,
        },
    )

    assert res.status_code == 200
    package_type.refresh_from_db()
    assert package_type.name == "BOX-NEW"
    assert package_type.description == "New desc"
    assert float(package_type.amount) == 12
    assert package_type.unit_of_measure is not None
    assert package_type.unit_of_measure.name == "BAL"
    assert res.json()["data"]["name"] == "BOX-NEW"
    assert res.json()["data"]["unit"] == "BAL"


def test_delete_package_type(db, client) -> None:
    package_type = PackageTypeFactory()

    res = client.delete(f"/{package_type.name}")

    assert res.status_code == 200
    assert res.json()["success"] is True


def test_preview_serial_returns_one_item_per_amount(db, client) -> None:
    receiving_location = WarehouseLocationFactory()
    warehouse_order = InboundWarehouseOrderFactory.it(
        pickup_location=receiving_location,
    )
    order_item = InboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        amount=10,
    )

    res = client.post(
        "/preview-serial",
        json={
            "order_item_id": order_item.pk,
            "product_code": order_item.stock_product.code,
            "amount": 4,
        },
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 4
    for item in data:
        assert item["tracking_level"] == TrackingLevel.SERIALIZED_PIECE
        assert item["amount"] == 1.0
        assert item["package"] is None
        assert item["batch"] is None
        assert item["location"]["code"] == receiving_location.code
        assert item["product"]["code"] == order_item.stock_product.code
        assert item["primary_barcode"] is not None


@pytest.mark.parametrize("amount", [0, -2, 2.5])
def test_preview_serial_requires_positive_whole_amount(db, client, amount) -> None:
    receiving_location = WarehouseLocationFactory()
    warehouse_order = InboundWarehouseOrderFactory.it(
        pickup_location=receiving_location,
    )
    order_item = InboundWarehouseOrderItemFactory.it(
        warehouse_order=warehouse_order,
        amount=10,
    )

    with pytest.raises(ApiBaseException) as exc:
        client.post(
            "/preview-serial",
            json={
                "order_item_id": order_item.pk,
                "product_code": order_item.stock_product.code,
                "amount": amount,
            },
        )

    assert exc.value.code == ErrorCode.INVALID_CONVERSION
