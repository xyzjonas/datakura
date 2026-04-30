from django.test import Client

from apps.warehouse.models.printer import Printer
from apps.warehouse.models.printer import UserAppSettings


def test_whoami_includes_default_printer(db, user) -> None:
    printer = Printer.objects.create(code="ZEBRA-DEFAULT", description="Default Zebra")
    UserAppSettings.objects.create(user=user, default_printer=printer)

    client = Client()
    client.force_login(user)

    response = client.get("/api/v1/auth/whoami")

    assert response.status_code == 200
    assert response.json()["data"]["default_printer"] == {
        "code": "ZEBRA-DEFAULT",
        "description": "Default Zebra",
        "created": printer.created.replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "changed": printer.changed.replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }


def test_set_default_printer_assigns_and_clears_printer(db, user) -> None:
    printer = Printer.objects.create(code="PACK-01", description="Packing")
    client = Client()
    client.force_login(user)

    assign_response = client.post(
        "/api/v1/auth/default-printer",
        data={"printer_code": printer.code},
        content_type="application/json",
    )

    assert assign_response.status_code == 200
    user.warehouse_app_settings.refresh_from_db()
    assert user.warehouse_app_settings.default_printer == printer

    clear_response = client.post(
        "/api/v1/auth/default-printer",
        data={"printer_code": None},
        content_type="application/json",
    )

    assert clear_response.status_code == 200
    user.warehouse_app_settings.refresh_from_db()
    assert user.warehouse_app_settings.default_printer is None
