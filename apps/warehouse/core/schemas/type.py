from __future__ import annotations

from ninja import Schema

from .base import BaseSchema, PaginatedResponse, Response


class ProductTypeSchema(BaseSchema):
    name: str


class ProductTypeCreateOrUpdateSchema(Schema):
    name: str


class GetProductTypeResponse(Response[ProductTypeSchema]): ...


class GetProductTypesResponse(PaginatedResponse[ProductTypeSchema]): ...
