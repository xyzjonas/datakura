from __future__ import annotations

from ninja import Schema

from .base import BaseResponse, Response
from .base import BaseSchema


class PrinterSchema(BaseSchema):
    code: str
    description: str | None = None


class GetPrintersResponse(BaseResponse):
    data: list[PrinterSchema]


class PrinterCreateOrUpdateSchema(Schema):
    code: str
    description: str | None = None


class GetPrinterResponse(Response[PrinterSchema]): ...


class DeletePrinterResponse(Response[PrinterSchema]): ...


class SetDefaultPrinterRequestSchema(Schema):
    printer_code: str | None = None


class SetDefaultPrinterResponse(BaseResponse):
    data: PrinterSchema | None = None
