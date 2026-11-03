from ninja import Schema
from pydantic import Field

from apps.warehouse.core.schemas.base import BaseSchema, PaginatedResponse, Response


class ShippingTypeSchema(BaseSchema):
    id: int
    name: str


class ShippingTypeCreateOrUpdateSchema(Schema):
    name: str = Field(..., min_length=1)


class GetShippingTypeResponse(Response[ShippingTypeSchema]): ...


class GetShippingTypesResponse(PaginatedResponse[ShippingTypeSchema]): ...


class OutboundOrderShippingSchema(BaseSchema):
    id: int
    shipping_type: ShippingTypeSchema | None = None
    package_number: str = ""
    width: float | None = None
    height: float | None = None
    depth: float | None = None
    name: str = ""
    state: str = ""
    city: str = ""
    street: str = ""
    postal_code: str = ""
    email: str = ""
    phone: str = ""
    price: float | None = None
    price_with_vat: float | None = None


class OutboundOrderShippingUpsertSchema(Schema):
    """Weight is deliberately missing: it is always derived from the order items."""

    shipping_type_id: int | None = None
    package_number: str = ""
    width: float | None = Field(None, ge=0)
    height: float | None = Field(None, ge=0)
    depth: float | None = Field(None, ge=0)
    name: str = ""
    state: str = Field("CZ", max_length=2)
    city: str = ""
    street: str = ""
    postal_code: str = ""
    email: str = ""
    phone: str = ""
    price: float | None = Field(None, ge=0)
    price_with_vat: float | None = Field(None, ge=0)
