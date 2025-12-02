from ninja import Schema
from pydantic import Field

from .base import BaseSchema, PaginatedResponse, BaseResponse
from .customer import CustomerSchema
from .product import ProductSchema


# --- IncomingOrderItem Schemas --- #


class IncomingOrderItemCreateSchema(Schema):
    product_code: str
    product_name: str
    amount: float
    unit_price: float


class IncomingOrderItemSchema(BaseSchema):
    product: ProductSchema
    amount: float
    unit_price: float


class IncomingOrderSchema(BaseSchema):
    code: str
    external_code: str | None = None
    description: str | None = None
    note: str | None = None
    supplier: CustomerSchema
    items: list[IncomingOrderItemSchema] = Field(default_factory=list)
    currency: str
    warehouse_order_code: str | None


class GetIncomingOrdersResponse(PaginatedResponse[IncomingOrderSchema]): ...


class CreateIncomingOrderItemResponse(BaseResponse):
    data: IncomingOrderItemSchema
