from __future__ import annotations

from ninja import Schema

from .base import BaseSchema, BaseResponse, PaginatedResponse, Response
from .warehouse import WarehouseItemSchema


class PackageTypeSchema(BaseSchema):
    name: str
    amount: float
    description: str | None = None
    unit: str | None = None


class GetPackageTypesResponse(BaseResponse):
    data: list[PackageTypeSchema]


class UnitOfMeasureSchema(BaseSchema):
    name: str
    amount_of_base_uom: float | None = None
    base_uom: str | None = None


class UnitOfMeasureCreateOrUpdateSchema(Schema):
    name: str
    amount_of_base_uom: float | None = None
    base_uom: str | None = None


class GetUnitOfMeasureResponse(Response[UnitOfMeasureSchema]): ...


class GetUnitOfMeasuresResponse(PaginatedResponse[UnitOfMeasureSchema]): ...


class PutInPackageRequestSchema(Schema):
    order_item_id: int
    product_code: str
    package_name: str
    amount: float


class PutInBatchRequestSchema(Schema):
    order_item_id: int
    product_code: str
    amount: float
    batch_code: str | None = None


class PutInSerialRequestSchema(Schema):
    order_item_id: int
    product_code: str
    amount: float


class PutInPackageResponse(BaseResponse):
    data: list[WarehouseItemSchema]
