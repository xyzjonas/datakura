from __future__ import annotations


from .base import BaseSchema, BaseResponse, PaginatedResponse


class ProductSchema(BaseSchema):
    name: str
    code: str
    type: str
    unit: str
    group: str | None = None
    unit_weight: float


class GetProductResponse(BaseResponse):
    data: ProductSchema


class GetProductsResponse(PaginatedResponse[ProductSchema]): ...
