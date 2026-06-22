from datetime import datetime
from typing import Literal

from ninja import Schema
from pydantic import Field

from .base import BaseSchema, BaseResponse
from .base_orders import (
    BaseOrder,
    OutboundWarehouseOrderBaseSchema,
    InboundWarehouseOrderBaseSchema,
)
from .product import ProductSchema


class ManufacturingOrderItemCreateSchema(Schema):
    in_product_code: str
    in_product_name: str
    in_amount: float
    out_product_code: str
    out_product_name: str
    out_amount: float
    index: int | None = None


class ManufacturingOrderItemSchema(BaseSchema):
    id: int
    in_product: ProductSchema
    in_amount: float
    out_product: ProductSchema
    out_amount: float
    index: int


class ManufacturingOrderCreateOrUpdateSchema(Schema):
    description: str | None = None
    note: str | None = None
    is_external: bool = False
    customer_code: str | None = None
    customer_name: str | None = None
    supplier_code: str | None = None
    supplier_name: str | None = None


class ManufacturingOrderTransitionSchema(Schema):
    action: Literal["next", "cancel"] = "next"


class ManufacturingOrderWarehouseOrderBaseSchema(BaseSchema):
    code: str
    state: str
    manufacturing_order_code: str


class ManufacturingOrderSchema(BaseOrder):
    description: str | None = None
    note: str | None = None
    is_external: bool
    cancelled_date: datetime | None = None
    completed_date: datetime | None = None
    items: list[ManufacturingOrderItemSchema] = Field(default_factory=list)
    outbound_warehouse_orders: list[OutboundWarehouseOrderBaseSchema] = Field(
        default_factory=list
    )
    inbound_warehouse_orders: list[InboundWarehouseOrderBaseSchema] = Field(
        default_factory=list
    )


class GetManufacturingOrderResponse(BaseResponse):
    data: ManufacturingOrderSchema


class CreateManufacturingOrderItemResponse(BaseResponse):
    data: ManufacturingOrderItemSchema
