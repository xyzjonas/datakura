from __future__ import annotations

from ninja import Schema
from pydantic import Field

from .base import BaseSchema, PaginatedResponse, Response
from .barcode import BarcodeSchema


class DynamicProductPriceCustomerSchema(Schema):
    code: str
    name: str


class DynamicProductPriceSchema(BaseSchema):
    price_id: int
    price_type: str
    discount_percent: float
    group: str | None = None
    customer: DynamicProductPriceCustomerSchema | None = None


class DynamicProductPriceCreateSchema(Schema):
    price_type: str
    discount_percent: float
    group_name: str | None = None
    customer_code: str | None = None


class DynamicProductPriceUpdateSchema(Schema):
    price_type: str | None = None
    discount_percent: float | None = None
    group_name: str | None = None
    customer_code: str | None = None


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
    dynamic_prices: list[DynamicProductPriceSchema] = Field(default_factory=list)


class ProductCreateOrUpdateSchema(Schema):
    name: str
    code: str
    type: str
    unit: str
    group: str | None = None
    unit_weight: float = 0
    base_price: float = 0
    purchase_price: float = 0
    currency: str = "CZK"
    customs_declaration_group: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


class ProductDuplicateSchema(ProductCreateOrUpdateSchema): ...


class GetProductResponse(Response[ProductSchema]): ...


class GetProductsResponse(PaginatedResponse[ProductSchema]): ...


class ProductBarcodeCreateSchema(Schema):
    code: str
    barcode_type: str = "EAN13"
    is_primary: bool = False
