from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from apps.warehouse.core.schemas.printer import (
    DeletePrinterResponse,
    GetPrinterResponse,
    GetPrintersResponse,
    PrinterCreateOrUpdateSchema,
)
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
