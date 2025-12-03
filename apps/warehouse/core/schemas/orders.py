from ninja import Schema
from pydantic import Field

from .base import BaseSchema, PaginatedResponse, BaseResponse
from .customer import CustomerSchema
from .product import ProductSchema
from apps.warehouse.models.orders import InboundOrderState


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


class InboundOrderTransitionSchema(Schema):
    state: InboundOrderState


class InboundOrderSchema(BaseSchema):
    code: str
    external_code: str | None = None
    description: str | None = None
    note: str | None = None
    supplier: CustomerSchema
    items: list[InboundOrderItemSchema] = Field(default_factory=list)
    currency: str
    warehouse_order_code: str | None
    state: InboundOrderState


class GetInboundOrderResponse(BaseResponse):
    data: InboundOrderSchema


class GetInboundOrdersResponse(PaginatedResponse[InboundOrderSchema]): ...


class CreateInboundOrderItemResponse(BaseResponse):
    data: InboundOrderItemSchema
