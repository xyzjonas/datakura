from __future__ import annotations


from .base import BaseSchema, BaseResponse


class ProductSchema(BaseSchema):
    name: str
    code: str
    type: str
    unit: str
    group: str | None = None


class GetProductResponse(BaseResponse):
    data: ProductSchema


class GetProductsResponse(BaseResponse):
    data: list[ProductSchema]
    count: int
    next: int | None
    previous: int | None
