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


def test_get_global_settings_code_sequence_defaults_to_yearly(db) -> None:
    response = TestClient(routes).get("")

    assert response.json()["data"]["code_sequence"] == "yearly"


@pytest.mark.parametrize("value", ["monthly", "yearly"])
def test_update_global_settings_code_sequence(db, value) -> None:
    response = TestClient(routes).put(
        "", json={"minimum_item_value": 0, "code_sequence": value}
    )

    assert response.status_code == 200
    assert response.json()["data"]["code_sequence"] == value
    assert GlobalSettings.load().code_sequence == value


def test_update_global_settings_without_code_sequence_keeps_it(db) -> None:
    GlobalSettingsFactory(code_sequence="monthly")

    response = TestClient(routes).put("", json={"minimum_item_value": 3})

    assert response.status_code == 200
    assert response.json()["data"]["code_sequence"] == "monthly"


def test_update_global_settings_code_sequence_only_keeps_minimum_value(db) -> None:
    GlobalSettingsFactory(minimum_item_value=7)

    response = TestClient(routes).put("", json={"code_sequence": "monthly"})

    assert response.status_code == 200
    assert response.json()["data"]["minimum_item_value"] == 7.0
    assert response.json()["data"]["code_sequence"] == "monthly"


@pytest.mark.parametrize("value", ["weekly", "", "YEARLY", 1])
def test_update_global_settings_rejects_unknown_code_sequence(db, value) -> None:
    response = TestClient(routes).put(
        "", json={"minimum_item_value": 0, "code_sequence": value}
    )

    assert response.status_code == 422
    assert GlobalSettings.load().code_sequence == "yearly"
