from datetime import datetime
from typing import Literal

from ninja import Schema
from pydantic import Field

from apps.warehouse.models.orders import InboundOrderState, OutboundOrderState
from .base import BaseSchema, PaginatedResponse, BaseResponse
from .base_orders import (
    InboundOrderBaseSchema,
    InboundWarehouseOrderBaseSchema,
    OutboundOrderBaseSchema,
    OutboundWarehouseOrderBaseSchema,
    CreditNoteBaseSchema,
)
from .invoice import InvoiceSchema
from .product import ProductSchema


# --- IncomingOrderItem Schemas --- #


class InboundOrderItemCreateSchema(Schema):
    product_code: str
    product_name: str
    amount: float
    total_price: float
    unit_price: float | None = None
    index: int | None = None


class InboundOrderItemSchema(BaseSchema):
    product: ProductSchema
    amount: float
    unit_price: float
    total_price: float
    index: int


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
    action: Literal["next", "cancel", "rollback"] = "next"


class InboundOrderSchema(InboundOrderBaseSchema):
    items: list[InboundOrderItemSchema] = Field(default_factory=list)
    state: InboundOrderState
    warehouse_orders: list[InboundWarehouseOrderBaseSchema] = Field(
        default_factory=list
    )
    credit_note: CreditNoteBaseSchema | None = None
    invoice: InvoiceSchema | None = None


class GetInboundOrderResponse(BaseResponse):
    data: InboundOrderSchema


class GetInboundOrdersResponse(PaginatedResponse[InboundOrderSchema]): ...


class CreateInboundOrderItemResponse(BaseResponse):
    data: InboundOrderItemSchema


class OutboundOrderItemCreateSchema(Schema):
    product_code: str
    product_name: str
    amount: float
    total_price: float
    unit_price: float | None = None
    index: int | None = None


class OutboundOrderItemSchema(BaseSchema):
    product: ProductSchema
    amount: float
    unit_price: float
    total_price: float
    index: int


class OutboundOrderCreateOrUpdateSchema(Schema):
    external_code: str | None = None
    description: str | None = None
    note: str | None = None
    currency: str
    customer_code: str
    customer_name: str
    state: OutboundOrderState | None = None
    requested_delivery_date: datetime | None = None


class OutboundOrderTransitionSchema(Schema):
    action: Literal["next", "cancel"] = "next"


class OutboundOrderSchema(OutboundOrderBaseSchema):
    items: list[OutboundOrderItemSchema] = Field(default_factory=list)
    state: OutboundOrderState
    warehouse_orders: list[OutboundWarehouseOrderBaseSchema] = Field(
        default_factory=list
    )
    credit_note: CreditNoteBaseSchema | None = None
    invoice: InvoiceSchema | None = None


class GetOutboundOrderResponse(BaseResponse):
    data: OutboundOrderSchema


class GetOutboundOrdersResponse(PaginatedResponse[OutboundOrderSchema]): ...


class CreateOutboundOrderItemResponse(BaseResponse):
    data: OutboundOrderItemSchema
