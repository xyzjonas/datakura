from __future__ import annotations

from pydantic import Field

from .base import BaseSchema, BaseResponse, PaginatedResponse


class ProductSchema(BaseSchema):
    name: str
    code: str
    type: str
    unit: str
    group: str | None = None
    unit_weight: float
    base_price: float
    purchase_price: float
    currency: str
    attributes: dict[str, str] = Field(default_factory=dict)


class GetProductResponse(BaseResponse):
    data: ProductSchema


class GetProductsResponse(PaginatedResponse[ProductSchema]): ...
