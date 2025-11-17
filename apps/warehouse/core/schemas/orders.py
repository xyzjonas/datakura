from pydantic import Field

from .base import BaseSchema, PaginatedResponse
from .customer import CustomerSchema
from .product import ProductSchema


# --- IncomingOrderItem Schemas --- #


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


class GetIncomingOrdersResponse(PaginatedResponse[IncomingOrderSchema]): ...
