from __future__ import annotations

from ninja import Schema
from pydantic import Field

from .base import BaseSchema, PaginatedResponse, Response
from .barcode import BarcodeSchema


class DynamicProductPriceCustomerSchema(Schema):
    code: str
    name: str


class DiscountGroupSchema(BaseSchema):
    code: str
    name: str
    discount_percent: float
    is_active: bool


class DiscountGroupCreateOrUpdateSchema(Schema):
    name: str
    discount_percent: float
    is_active: bool = True


class DynamicProductPriceSchema(BaseSchema):
    price_id: int
    fixed_price: float
    discount_percent: float
    customer: DynamicProductPriceCustomerSchema


class SellingPriceLookupSchema(Schema):
    product_code: str
    customer_code: str | None = None
    base_price: float
    final_price: float
    discount_percent: float
    reason: str
    source: str


class DynamicProductPriceCreateSchema(Schema):
    fixed_price: float
    customer_code: str


class DynamicProductPriceUpdateSchema(Schema):
    fixed_price: float | None = None
    customer_code: str | None = None


class CustomerPriceOverrideUpsertSchema(Schema):
    customer_code: str
    fixed_price: float


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


class GetSellingPriceLookupResponse(Response[SellingPriceLookupSchema]): ...


class GetProductsResponse(PaginatedResponse[ProductSchema]): ...


class GetDiscountGroupResponse(Response[DiscountGroupSchema]): ...


class GetDiscountGroupsResponse(Response[list[DiscountGroupSchema]]): ...


class ProductBarcodeCreateSchema(Schema):
    code: str
    barcode_type: str = "EAN13"
    is_primary: bool = False
