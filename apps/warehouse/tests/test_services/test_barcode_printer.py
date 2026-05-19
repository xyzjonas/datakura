from unittest.mock import patch

import pytest

from apps.warehouse.core.exceptions import ApiBaseException, NotFoundException
from apps.warehouse.core.services.barcode_printer import barcode_printer_service
from apps.warehouse.models.printer import Printer, UserAppSettings


@pytest.fixture
def printer(db) -> Printer:
    return Printer.objects.create(
        code="ZEBRA-PRINT-01",
        description="Test printer",
        ip="10.20.30.40",
        port=9100,
    )


def test_print_barcode_with_explicit_printer(db, user, printer):
    with patch(
        "apps.warehouse.core.services.barcode_printer.zebra_printer.print_barcode"
    ) as mock_print:
        result = barcode_printer_service.print_barcode(
            user=user,
            barcode="WMS-001",
            text="Hello",
            printer_code=printer.code,
            copies=2,
        )

    mock_print.assert_called_once_with(
        barcode="WMS-001",
        text="Hello",
        ip="10.20.30.40",
        port=9100,
        copies=2,
    )
    assert result.printer_code == "ZEBRA-PRINT-01"
    assert result.copies == 2


def test_print_barcode_uses_user_default_when_no_printer_code(db, user, printer):
    UserAppSettings.objects.create(user=user, default_printer=printer)

    with patch(
        "apps.warehouse.core.services.barcode_printer.zebra_printer.print_barcode"
    ) as mock_print:
        result = barcode_printer_service.print_barcode(user=user, barcode="WMS-001")

    mock_print.assert_called_once()
    assert mock_print.call_args.kwargs["ip"] == "10.20.30.40"
    assert result.printer_code == printer.code


def test_print_barcode_no_printer_and_no_default_raises(db, user):
    with pytest.raises(ApiBaseException, match="No printer specified"):
        barcode_printer_service.print_barcode(user=user, barcode="WMS-001")


def test_print_barcode_unknown_printer_code_raises(db, user):
    with pytest.raises(NotFoundException):
        barcode_printer_service.print_barcode(
            user=user, barcode="WMS-001", printer_code="DOES-NOT-EXIST"
        )


def test_print_barcode_printer_without_ip_raises(db, user):
    Printer.objects.create(code="NO-IP", description="missing ip", ip=None)
    with pytest.raises(ApiBaseException, match="no IP address"):
        barcode_printer_service.print_barcode(
            user=user, barcode="WMS-001", printer_code="NO-IP"
        )


def test_print_barcode_invalid_copies_raises(db, user, printer):
    with pytest.raises(ApiBaseException, match="at least 1"):
        barcode_printer_service.print_barcode(
            user=user, barcode="WMS-001", printer_code=printer.code, copies=0
        )


def test_print_barcode_connection_error_becomes_502(db, user, printer):
    with patch(
        "apps.warehouse.core.services.barcode_printer.zebra_printer.print_barcode",
        side_effect=ConnectionError("boom"),
    ):
        with pytest.raises(ApiBaseException) as excinfo:
            barcode_printer_service.print_barcode(
                user=user, barcode="WMS-001", printer_code=printer.code
            )
    assert excinfo.value.http_status == 502


def test_print_barcode_empty_barcode_propagates_as_400(db, user, printer):
    with patch(
        "apps.warehouse.core.services.barcode_printer.zebra_printer.print_barcode",
        side_effect=ValueError("Barcode cannot be empty"),
    ):
        with pytest.raises(ApiBaseException) as excinfo:
            barcode_printer_service.print_barcode(
                user=user, barcode="", printer_code=printer.code
            )
    assert excinfo.value.http_status == 400
