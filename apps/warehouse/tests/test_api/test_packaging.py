import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.packaging import routes
from apps.warehouse.core.exceptions import ApiBaseException, ErrorCode
from apps.warehouse.models.warehouse import TrackingLevel
from apps.warehouse.tests.factories.warehouse import WarehouseItemFactory


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def test_preview_serial_returns_one_item_per_amount(db, client) -> None:
    warehouse_item = WarehouseItemFactory.it(amount=10)

    res = client.post(
        "/preview-serial",
        json={
            "warehouse_item_id": warehouse_item.pk,
            "product_code": warehouse_item.stock_product.code,
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
        assert item["location"]["code"] == warehouse_item.location.code
        assert item["product"]["code"] == warehouse_item.stock_product.code
        assert item["primary_barcode"] is not None


@pytest.mark.parametrize("amount", [0, -2, 2.5])
def test_preview_serial_requires_positive_whole_amount(db, client, amount) -> None:
    warehouse_item = WarehouseItemFactory.it(amount=10)

    with pytest.raises(ApiBaseException) as exc:
        client.post(
            "/preview-serial",
            json={
                "warehouse_item_id": warehouse_item.pk,
                "product_code": warehouse_item.stock_product.code,
                "amount": amount,
            },
        )

    assert exc.value.code == ErrorCode.INVALID_CONVERSION
