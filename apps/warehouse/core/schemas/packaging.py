from __future__ import annotations

from ninja import Schema

from .base import BaseSchema, BaseResponse
from .warehouse import WarehouseItemSchema


class PackageTypeSchema(BaseSchema):
    name: str
    amount: float
    description: str
    unit: str


class GetPackageTypesResponse(BaseResponse):
    data: list[PackageTypeSchema]


class PutInPackageRequestSchema(Schema):
    warehouse_item_id: int
    product_code: str
    package_name: str
    amount: float


class PutInPackageResponse(BaseResponse):
    data: list[WarehouseItemSchema]
