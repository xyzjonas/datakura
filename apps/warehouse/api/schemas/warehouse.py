from __future__ import annotations

from .base import BaseResponse, BaseSchema


class StockItemSchema(BaseSchema):
    name: str
    code: str


class PackageSchema(BaseSchema):
    code: str
    type: str
    description: str | None
    amount: float
    unit: str


class WarehouseItemSchema(BaseSchema):
    """Atomic unit of the inventory - uniquely identifiable and trackable item in a warehouse"""

    code: str
    stock_item: StockItemSchema
    unit_of_measure: str
    amount: float
    package: PackageSchema | None


class WarehouseLocationSchema(BaseSchema):
    code: str


class WarehouseLocationDetailSchema(WarehouseLocationSchema):
    items: list[WarehouseItemSchema]


class WarehouseSchema(BaseSchema):
    name: str
    description: str | None
    locations: list[WarehouseLocationSchema]


class WarehouseExpandedSchema(BaseSchema):
    name: str
    description: str | None
    locations: list[WarehouseLocationDetailSchema]


class GetWarehousesResponse(BaseResponse):
    data: list[WarehouseSchema]


class GetWarehouseLocationResponse(BaseResponse):
    data: WarehouseLocationDetailSchema


class GetProductWarehouseInfoResponse(BaseResponse):
    data: list[WarehouseExpandedSchema]
