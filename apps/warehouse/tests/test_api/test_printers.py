from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from ninja.testing import TestClient

from apps.warehouse.api.routes.printers import routes
from apps.warehouse.core.exceptions import ApiBaseException
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


def test_print_barcode_with_explicit_printer_code(db, client) -> None:
    Printer.objects.create(
        code="ZEBRA-PRT", description="Pack", ip="10.0.0.1", port=9100
    )

    with patch(
        "apps.warehouse.core.services.barcode_printer.zebra_printer.print_barcode"
    ) as mock_print:
        res = client.post(
            "/print?printer_code=ZEBRA-PRT",
            json={"barcode": "WMS-001", "text": "Hello", "copies": 2},
        )

    assert res.status_code == 200, res.json()
    body = res.json()
    assert body["success"] is True
    assert body["data"] == {"printer_code": "ZEBRA-PRT", "copies": 2}
    mock_print.assert_called_once_with(
        barcode="WMS-001", text="Hello", ip="10.0.0.1", port=9100, copies=2
    )


def test_print_barcode_falls_back_to_user_default_printer(db, client, user) -> None:
    printer = Printer.objects.create(
        code="ZEBRA-DEFAULT", description="Default", ip="10.0.0.2", port=9100
    )
    UserAppSettings.objects.create(user=user, default_printer=printer)

    with patch(
        "apps.warehouse.core.services.barcode_printer.zebra_printer.print_barcode"
    ) as mock_print:
        res = client.post("/print", json={"barcode": "WMS-002"})

    assert res.status_code == 200
    assert res.json()["data"]["printer_code"] == "ZEBRA-DEFAULT"
    mock_print.assert_called_once()
    assert mock_print.call_args.kwargs["ip"] == "10.0.0.2"


def test_print_barcode_no_printer_raises(db, client) -> None:
    with pytest.raises(ApiBaseException, match="No printer specified"):
        client.post("/print", json={"barcode": "WMS-003"})
