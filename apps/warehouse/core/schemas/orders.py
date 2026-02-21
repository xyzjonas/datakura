from datetime import datetime
from ninja import Schema
from pydantic import Field

from apps.warehouse.models.orders import InboundOrderState
from .base import BaseSchema, PaginatedResponse, BaseResponse
from .base_orders import (
    InboundOrderBaseSchema,
    InboundWarehouseOrderBaseSchema,
    CreditNoteBaseSchema,
)
from .product import ProductSchema


# --- IncomingOrderItem Schemas --- #


class InboundOrderItemCreateSchema(Schema):
    product_code: str
    product_name: str
    amount: float
    unit_price: float


class InboundOrderItemSchema(BaseSchema):
    product: ProductSchema
    amount: float
    unit_price: float


class InboundOrderCreateOrUpdateSchema(Schema):
    external_code: str | None = None
    description: str | None = None
    note: str | None = None
    currency: str
    supplier_code: str
    supplier_name: str
    state: InboundOrderState | None = None
    requested_delivery_date: datetime | None = None


class InboundOrderTransitionSchema(Schema):
    state: InboundOrderState


class InboundOrderSchema(InboundOrderBaseSchema):
    items: list[InboundOrderItemSchema] = Field(default_factory=list)
    state: InboundOrderState
    warehouse_order: InboundWarehouseOrderBaseSchema | None = None
    credit_note: CreditNoteBaseSchema | None = None


class GetInboundOrderResponse(BaseResponse):
    data: InboundOrderSchema


class GetInboundOrdersResponse(PaginatedResponse[InboundOrderSchema]): ...


class CreateInboundOrderItemResponse(BaseResponse):
    data: InboundOrderItemSchema
