from __future__ import annotations

from ninja import Schema

from .base import BaseResponse, BaseSchema


class StockItemSchema(BaseSchema):
    name: str
    code: str


class PackageSchema(BaseSchema):
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


class ProductWarehouseAvailability(Schema):
    """Summary of item's availability in the warehouse"""

    total_amount: float
    available_amount: float


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


class WarehouseOrderSchema(BaseSchema):
    code: str
    items: list[WarehouseItemSchema]
    order_code: str | None


class GetWarehousesResponse(BaseResponse):
    data: list[WarehouseSchema]


class GetWarehouseLocationResponse(BaseResponse):
    data: WarehouseLocationDetailSchema


class GetProductWarehouseAvailabilityResponse(BaseResponse):
    data: ProductWarehouseAvailability


class GetProductWarehouseInfoResponse(BaseResponse):
    data: list[WarehouseExpandedSchema]


class GetWarehouseOrderResponse(BaseResponse):
    data: WarehouseOrderSchema
