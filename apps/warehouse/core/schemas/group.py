from __future__ import annotations

from ninja import Schema

from .base import BaseSchema, PaginatedResponse, Response


class ProductGroupSchema(BaseSchema):
    name: str


class ProductGroupCreateOrUpdateSchema(Schema):
    name: str


class GetProductGroupResponse(Response[ProductGroupSchema]): ...


class GetProductGroupsResponse(PaginatedResponse[ProductGroupSchema]): ...
