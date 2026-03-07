from __future__ import annotations

from ninja import Schema
from pydantic import Field

from .base import BaseSchema, BaseResponse, PaginatedResponse
from .barcode import BarcodeSchema


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
    customs_declaration_group: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    barcodes: list[BarcodeSchema] = Field(default_factory=list)
    primary_barcode: BarcodeSchema | None = None


class GetProductResponse(BaseResponse):
    data: ProductSchema


class GetProductsResponse(PaginatedResponse[ProductSchema]): ...


class ProductBarcodeCreateSchema(Schema):
    code: str
    barcode_type: str = "EAN13"
    is_primary: bool = False
