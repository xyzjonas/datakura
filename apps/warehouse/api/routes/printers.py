from __future__ import annotations

from typing import cast

from django.contrib.auth.models import User
from django.http import HttpRequest
from ninja import Router

from apps.warehouse.core.schemas.printer import (
    DeletePrinterResponse,
    GetPrinterResponse,
    GetPrintersResponse,
    PrintBarcodeRequestSchema,
    PrintBarcodeResponse,
    PrinterCreateOrUpdateSchema,
)
from apps.warehouse.core.services.barcode_printer import barcode_printer_service
from apps.warehouse.core.services.printers import printers_service
from apps.warehouse.core.transformation import printer_orm_to_schema

routes = Router(tags=["printers"])


@routes.get("", response={200: GetPrintersResponse})
def get_printers(request: HttpRequest, search_term: str | None = None):
    return GetPrintersResponse(
        data=[
            printer_orm_to_schema(printer)
            for printer in printers_service.get_printers(search_term)
        ]
    )


@routes.post("", response={200: GetPrinterResponse})
def create_printer(request: HttpRequest, body: PrinterCreateOrUpdateSchema):
    return GetPrinterResponse(data=printers_service.create_printer(body))


@routes.post("/print", response={200: PrintBarcodeResponse})
def print_barcode(
    request: HttpRequest,
    body: PrintBarcodeRequestSchema,
    printer_code: str | None = None,
):
    return PrintBarcodeResponse(
        data=barcode_printer_service.print_barcode(
            user=cast(User, request.user),
            barcode=body.barcode,
            text=body.text,
            printer_code=printer_code,
            copies=body.copies,
        )
    )


@routes.put("/{printer_code}", response={200: GetPrinterResponse})
def update_printer(
    request: HttpRequest,
    printer_code: str,
    body: PrinterCreateOrUpdateSchema,
):
    return GetPrinterResponse(data=printers_service.update_printer(printer_code, body))


@routes.delete("/{printer_code}", response={200: DeletePrinterResponse})
def delete_printer(request: HttpRequest, printer_code: str):
    return DeletePrinterResponse(data=printers_service.delete_printer(printer_code))
