import pytest
from ninja.testing import TestClient

from apps.warehouse.api.routes.settings import routes
from apps.warehouse.models.settings import GlobalSettings
from apps.warehouse.tests.factories.settings import GlobalSettingsFactory


def test_get_global_settings_defaults_to_no_minimum(db) -> None:
    client = TestClient(routes)

    response = client.get("")

    assert response.status_code == 200
    assert response.json()["data"]["minimum_item_value"] == 0.0


def test_get_global_settings_returns_stored_value(db) -> None:
    GlobalSettingsFactory(minimum_item_value=5)
    client = TestClient(routes)

    response = client.get("")

    assert response.json()["data"]["minimum_item_value"] == 5.0


@pytest.mark.parametrize("value", [0, 0.5, 20, 1234.5678])
def test_update_global_settings(db, value) -> None:
    client = TestClient(routes)

    response = client.put("", json={"minimum_item_value": value})

    assert response.status_code == 200
    assert response.json()["data"]["minimum_item_value"] == value
    assert float(GlobalSettings.load().minimum_item_value) == value
    assert GlobalSettings.objects.count() == 1


def test_update_global_settings_rejects_negative_value(db) -> None:
    client = TestClient(routes)

    response = client.put("", json={"minimum_item_value": -1})

    assert response.status_code == 422
    assert GlobalSettings.load().minimum_item_value == 0
