from __future__ import annotations

from ninja import Schema

from .base import BaseSchema, BaseResponse


class ConversionFactorSchema(Schema):
    unit_of_measure: str
    factor: float


class ProductSchema(BaseSchema):
    name: str
    code: str
    type: str
    unit: str
    group: str | None = None
    conversion_factors: list[ConversionFactorSchema]


class GetProductResponse(BaseResponse):
    data: ProductSchema


class GetProductsResponse(BaseResponse):
    data: list[ProductSchema]
