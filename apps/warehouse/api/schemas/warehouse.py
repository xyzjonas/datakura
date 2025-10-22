from __future__ import annotations

from .base import BaseResponse, BaseSchema


class StockItemSchema(BaseSchema):
    name: str
    code: str


class PackageTypeSchema(BaseSchema):
    name: str
    description: str | None
    count: int


class WarehouseItemSchema(BaseSchema):
    """Atomic unit of the inventory - uniquely identifiable and trackable item in a warehouse"""

    stock_item: StockItemSchema
    package_type: PackageTypeSchema
    remaining: int


class WarehouseLocationSchema(BaseSchema):
    code: str


class WarehouseLocationDetailSchema(WarehouseLocationSchema):
    items: list[WarehouseItemSchema]


class WarehouseSchema(BaseSchema):
    name: str
    description: str | None
    locations: list[WarehouseLocationSchema]


class GetWarehousesResponse(BaseResponse):
    data: list[WarehouseSchema]


class GetWarehouseLocationResponse(BaseResponse):
    data: WarehouseLocationDetailSchema
