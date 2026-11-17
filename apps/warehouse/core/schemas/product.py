from __future__ import annotations

from datetime import datetime
from typing import Annotated

from ninja import Schema
from pydantic import Field, StringConstraints, field_serializer, field_validator

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
    min_amount: float | None = None
    customer: DynamicProductPriceCustomerSchema


class CustomerProductCodeSchema(BaseSchema):
    id: int
    code: str
    customer: DynamicProductPriceCustomerSchema


class CustomerProductCodeUpsertSchema(Schema):
    customer_code: str
    code: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]


class CustomerProductCodeUpdateSchema(Schema):
    code: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]


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


def _normalize_customs_code(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


class ProductSchema(BaseSchema):
    name: str
    code: str
    type: str
    # derived from the product type - such products are never picked
    non_physical: bool = False
    unit: str
    group: str | None = None
    unit_weight: float
    base_price: float
    purchase_price: float
    base_price_changed: datetime
    purchase_price_changed: datetime
    no_discount: bool
    disallow_unpacking: bool
    currency: str
    customs_declaration_group: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    barcodes: list[BarcodeSchema] = Field(default_factory=list)
    primary_barcode: BarcodeSchema | None = None
    dynamic_prices: list[DynamicProductPriceSchema] = Field(default_factory=list)

    @field_serializer("base_price_changed", "purchase_price_changed")
    def serialize_price_changed(self, dt: datetime) -> datetime:
        # same as `created` / `changed`: no microseconds
        return dt.replace(microsecond=0)


class ProductCreateOrUpdateSchema(Schema):
    name: str
    code: str
    type: str
    unit: str
    group: str | None = None
    unit_weight: float = Field(0, ge=0)
    base_price: float = 0
    purchase_price: float = 0
    no_discount: bool = False
    disallow_unpacking: bool = False
    currency: str = "CZK"
    customs_declaration_group: str | None = Field(None, max_length=255)
    attributes: dict[str, str] = Field(default_factory=dict)

    @field_validator("customs_declaration_group")
    @classmethod
    def _normalize_customs_code(cls, value: str | None) -> str | None:
        return _normalize_customs_code(value)


class ProductBasePriceSchema(Schema):
    """Narrow correction payload used when ordering new stock (inbound order)."""

    base_price: float = Field(..., ge=0)


class ProductCustomsWeightSchema(Schema):
    """Narrow correction payload used during goods receiving."""

    unit_weight: float = Field(..., gt=0)
    customs_declaration_group: str | None = Field(None, max_length=255)

    @field_validator("customs_declaration_group")
    @classmethod
    def _normalize_customs_code(cls, value: str | None) -> str | None:
        return _normalize_customs_code(value)


class ProductDuplicateSchema(ProductCreateOrUpdateSchema): ...


class GetProductResponse(Response[ProductSchema]): ...


class GetCustomerProductCodeResponse(Response[CustomerProductCodeSchema]): ...


class GetCustomerProductCodesResponse(Response[list[CustomerProductCodeSchema]]): ...


class GetSellingPriceLookupResponse(Response[SellingPriceLookupSchema]): ...


class GetProductsResponse(PaginatedResponse[ProductSchema]): ...


class GetDiscountGroupResponse(Response[DiscountGroupSchema]): ...


class GetDiscountGroupsResponse(Response[list[DiscountGroupSchema]]): ...


class ProductBarcodeCreateSchema(Schema):
    code: str
    barcode_type: str = "EAN13"
    is_primary: bool = False


class ProductBarcodeUpdateSchema(Schema):
    code: str | None = None
    barcode_type: str | None = None
    is_primary: bool | None = None


class BarcodeGenerateSchema(Schema):
    barcode_type: str = "EAN13"
    prefix: str | None = None
    length: int | None = None
    country_code: str | None = None
    numeric_only: bool | None = None
    include_letters: bool | None = None
    include_digits: bool | None = None


class BarcodeGenerateResponseSchema(Schema):
    code: str
    barcode_type: str


class GetBarcodeGenerateResponse(Response[BarcodeGenerateResponseSchema]): ...
