from __future__ import annotations

from ninja import Schema

from .barcode import BarcodeSchema
from .base import BaseResponse, BaseSchema, EmptyResponse, PaginatedResponse, Response
from .warehouse import WarehouseItemSchema


class PackageTypeSchema(BaseSchema):
    name: str
    amount: float
    description: str | None = None
    unit: str | None = None


class GetPackageTypesResponse(BaseResponse):
    data: list[PackageTypeSchema]


class PackageTypeCreateOrUpdateSchema(Schema):
    name: str
    amount: float
    description: str | None = None
    unit: str | None = None


class GetPackageTypeResponse(Response[PackageTypeSchema]): ...


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


class DeletePackageTypeResponse(EmptyResponse): ...


class BatchSchema(BaseSchema):
    id: int
    primary_barcode: BarcodeSchema | None
    description: str | None


class BatchCreateOrUpdateSchema(Schema):
    barcode: str | None = None
    description: str | None = None
    auto_generate_barcode: bool = False


class GetBatchResponse(Response[BatchSchema]): ...


class GetBatchesResponse(PaginatedResponse[BatchSchema]): ...


class DeleteBatchResponse(EmptyResponse): ...
