import pytest
from django.contrib.auth.models import User
from ninja.testing import TestClient

from apps.warehouse.api.routes.printers import routes
from apps.warehouse.models.printer import Printer, UserAppSettings


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def test_get_printers_with_search(db, client) -> None:
    Printer.objects.create(code="ZEBRA-01", description="Zebra warehouse")
    Printer.objects.create(code="OFFICE-01", description="Office laser")

    res = client.get("/?search_term=zebra")

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["code"] == "ZEBRA-01"


def test_create_printer(db, client) -> None:
    res = client.post(
        "/",
        json={
            "code": "ZEBRA-02",
            "description": "Packing table printer",
        },
    )

    assert res.status_code == 200
    assert res.json()["data"]["code"] == "ZEBRA-02"
    assert res.json()["data"]["description"] == "Packing table printer"


def test_update_printer(db, client) -> None:
    printer = Printer.objects.create(code="OLD-01", description="Old printer")

    res = client.put(
        f"/{printer.code}",
        json={
            "code": "NEW-01",
            "description": "New printer",
        },
    )

    assert res.status_code == 200
    printer.refresh_from_db()
    assert printer.code == "NEW-01"
    assert printer.description == "New printer"


def test_delete_printer_unassigns_default_printer(db, client) -> None:
    printer = Printer.objects.create(code="ZEBRA-03", description="Delete me")
    settings_obj = UserAppSettings.objects.create(
        user=User.objects.create_user(username="printer-delete-user"),
        default_printer=printer,
    )
    printer_code = printer.code

    res = client.delete(f"/{printer_code}")

    assert res.status_code == 200
    settings_obj.refresh_from_db()
    assert settings_obj.default_printer is None
    assert not Printer.objects.filter(code=printer_code).exists()
