from __future__ import annotations

from ninja import Schema

from .base import BaseSchema, PaginatedResponse, Response


class ProductTypeSchema(BaseSchema):
    name: str
    non_physical: bool = False


class ProductTypeCreateOrUpdateSchema(Schema):
    name: str
    non_physical: bool = False


class GetProductTypeResponse(Response[ProductTypeSchema]): ...


class GetProductTypesResponse(PaginatedResponse[ProductTypeSchema]): ...
