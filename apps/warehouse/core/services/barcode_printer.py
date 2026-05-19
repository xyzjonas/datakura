from __future__ import annotations

from django.contrib.auth.models import User

from apps.warehouse.core import zebra_printer
from apps.warehouse.core.exceptions import ApiBaseException, NotFoundException
from apps.warehouse.core.schemas.printer import PrintBarcodeResultSchema
from apps.warehouse.models.printer import Printer, UserAppSettings


def _resolve_printer(user: User, printer_code: str | None) -> Printer:
    if printer_code:
        try:
            return Printer.objects.get(code=printer_code)
        except Printer.DoesNotExist:
            raise NotFoundException(f"Printer '{printer_code}' not found")

    settings_obj = (
        UserAppSettings.objects.select_related("default_printer")
        .filter(user=user)
        .first()
    )
    if not settings_obj or not settings_obj.default_printer:
        raise ApiBaseException(
            "No printer specified and no default printer set for user",
            http_status=400,
        )
    return settings_obj.default_printer


class BarcodePrinterService:
    @staticmethod
    def print_barcode(
        user: User,
        barcode: str,
        text: str = "",
        printer_code: str | None = None,
        copies: int = 1,
    ) -> PrintBarcodeResultSchema:
        if copies < 1:
            raise ApiBaseException("Copies must be at least 1", http_status=400)

        printer = _resolve_printer(user, printer_code)

        if not printer.ip:
            raise ApiBaseException(
                f"Printer '{printer.code}' has no IP address configured",
                http_status=400,
            )

        try:
            zebra_printer.print_barcode(
                barcode=barcode,
                text=text,
                ip=printer.ip,
                port=printer.port,
                copies=copies,
            )
        except ValueError as exc:
            raise ApiBaseException(str(exc), http_status=400)
        except (ConnectionError, TimeoutError) as exc:
            raise ApiBaseException(str(exc), http_status=502)

        return PrintBarcodeResultSchema(printer_code=printer.code, copies=copies)


barcode_printer_service = BarcodePrinterService()
