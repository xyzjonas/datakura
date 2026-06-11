from decimal import Decimal

import pytest
from ninja.testing import TestClient

from apps.warehouse.api.app import api
from apps.warehouse.api.routes.warehouse import routes
from apps.warehouse.core.exceptions import (
    WarehouseItemBadRequestError,
    WarehouseItemNotFoundError,
)
from apps.warehouse.core.schemas.warehouse import MoveItemRequest
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.warehouse import (
    TrackingLevel,
    WarehouseItem,
    WarehouseLocation,
    WarehouseMovement,
)
from apps.warehouse.tests.factories.packaging import PackageTypeFactory
from apps.warehouse.tests.factories.warehouse import (
    WarehouseItemFactory,
    WarehouseLocationFactory,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


@pytest.fixture
def full_client() -> TestClient:
    return TestClient(api)


# ---------------------------------------------------------------------------
# Happy path (via routes TestClient)
# ---------------------------------------------------------------------------


def test_move_serialized_piece(db, client) -> None:
    location_from: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    location_to: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    item: WarehouseItem = WarehouseItemFactory(  # type: ignore
        location=location_from,
        tracking_level=TrackingLevel.SERIALIZED_PIECE,
        amount=Decimal("1"),
    )

    res = client.post(
        "movement",
        json={"item_id": item.pk, "location_to_code": location_to.code},
    )

    assert res.status_code == 200, res.json()
    item.refresh_from_db()
    assert item.location == location_to
    assert WarehouseMovement.objects.filter(item=item, location_to=location_to).exists()


def test_move_fungible_partial(db, client) -> None:
    location_from: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    location_to: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    item: WarehouseItem = WarehouseItemFactory(  # type: ignore
        location=location_from,
        tracking_level=TrackingLevel.FUNGIBLE,
        amount=Decimal("100"),
    )

    res = client.post(
        "movement",
        json={"item_id": item.pk, "location_to_code": location_to.code, "amount": 40},
    )

    assert res.status_code == 200, res.json()
    item.refresh_from_db()
    assert item.amount == Decimal("60")
    new_item = WarehouseItem.objects.get(
        location=location_to, stock_product=item.stock_product
    )
    assert new_item.amount == Decimal("40")


def test_move_fungible_full(db, client) -> None:
    location_from: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    location_to: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    item: WarehouseItem = WarehouseItemFactory(  # type: ignore
        location=location_from,
        tracking_level=TrackingLevel.FUNGIBLE,
        amount=Decimal("50"),
    )

    res = client.post(
        "movement",
        json={"item_id": item.pk, "location_to_code": location_to.code},
    )

    assert res.status_code == 200, res.json()
    item.refresh_from_db()
    assert item.location == location_to


def test_move_package_with_unpack(db, client) -> None:
    location_from: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    location_to: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    pkg_type = PackageTypeFactory()
    item: WarehouseItem = WarehouseItemFactory(  # type: ignore
        location=location_from,
        tracking_level=TrackingLevel.SERIALIZED_PACKAGE,
        amount=Decimal("10"),
        package_type=pkg_type,
    )

    res = client.post(
        "movement",
        json={
            "item_id": item.pk,
            "location_to_code": location_to.code,
            "amount": 3,
            "unpack": True,
        },
    )

    assert res.status_code == 200, res.json()
    item.refresh_from_db()
    assert item.amount == Decimal("7")
    unpacked = WarehouseItem.objects.get(location=location_to, unpacked_from=item)
    assert unpacked.amount == Decimal("3")


# ---------------------------------------------------------------------------
# Edge cases / error paths (tested via service to avoid exception handler gap)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("amount", [0, -1, -100])
def test_move_rejects_non_positive_amount(db, context, amount) -> None:
    location: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    item: WarehouseItem = WarehouseItemFactory(location=location, amount=Decimal("10"))  # type: ignore

    with pytest.raises(WarehouseItemBadRequestError):
        warehouse_service.move_item_standalone(
            MoveItemRequest(
                item_id=item.pk,
                location_to_code=str(location.code),
                amount=amount,
            ),
            context=context,
        )


def test_move_rejects_amount_exceeding_stock(db, context) -> None:
    location_from: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    location_to: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    item: WarehouseItem = WarehouseItemFactory(
        location=location_from, amount=Decimal("5")
    )  # type: ignore

    with pytest.raises(WarehouseItemBadRequestError):
        warehouse_service.move_item_standalone(
            MoveItemRequest(
                item_id=item.pk,
                location_to_code=str(location_to.code),
                amount=Decimal("99"),
            ),
            context=context,
        )


def test_move_rejects_same_location(db, context) -> None:
    location: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    item: WarehouseItem = WarehouseItemFactory(location=location, amount=Decimal("5"))  # type: ignore

    with pytest.raises(WarehouseItemBadRequestError):
        warehouse_service.move_item_standalone(
            MoveItemRequest(item_id=item.pk, location_to_code=str(location.code)),
            context=context,
        )


def test_move_not_found_item(db, context) -> None:
    location: WarehouseLocation = WarehouseLocationFactory()  # type: ignore

    with pytest.raises(WarehouseItemNotFoundError):
        warehouse_service.move_item_standalone(
            MoveItemRequest(item_id=999999, location_to_code=str(location.code)),
            context=context,
        )


def test_move_unpack_requires_amount(db, context) -> None:
    location_from: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    location_to: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    pkg_type = PackageTypeFactory()
    item: WarehouseItem = WarehouseItemFactory(  # type: ignore
        location=location_from,
        tracking_level=TrackingLevel.SERIALIZED_PACKAGE,
        amount=Decimal("10"),
        package_type=pkg_type,
    )

    with pytest.raises(WarehouseItemBadRequestError):
        warehouse_service.move_item_standalone(
            MoveItemRequest(
                item_id=item.pk,
                location_to_code=str(location_to.code),
                unpack=True,
            ),
            context=context,
        )


def test_move_unpack_only_valid_for_package(db, context) -> None:
    location_from: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    location_to: WarehouseLocation = WarehouseLocationFactory()  # type: ignore
    item: WarehouseItem = WarehouseItemFactory(  # type: ignore
        location=location_from,
        tracking_level=TrackingLevel.FUNGIBLE,
        amount=Decimal("10"),
    )

    with pytest.raises(WarehouseItemBadRequestError):
        warehouse_service.move_item_standalone(
            MoveItemRequest(
                item_id=item.pk,
                location_to_code=str(location_to.code),
                amount=Decimal("3"),
                unpack=True,
            ),
            context=context,
        )
