from datetime import datetime
from typing import Annotated, Literal

from ninja import Schema
from pydantic import Field

from apps.warehouse.models.orders import InboundOrderState, OutboundOrderState
from .base import BaseSchema, PaginatedResponse, BaseResponse
from .base_orders import (
    InboundWarehouseOrderBaseSchema,
    OutboundWarehouseOrderBaseSchema,
    CreditNoteBaseSchema,
    BaseOrder,
)
from .customer import ContactPersonSchema
from .invoice import InvoiceSchema
from .product import ProductSchema


# --- IncomingOrderItem Schemas --- #


class InboundOrderItemCreateSchema(Schema):
    product_code: str
    product_name: str
    amount: Annotated[float, Field(gt=0, lt=1_000_000)]
    total_price: Annotated[float, Field(ge=0, lt=100_000_000)]
    unit_price: float | None = None
    index: int | None = None


class InboundOrderItemSchema(BaseSchema):
    product: ProductSchema
    amount: float
    unit_price: float
    total_price: float
    index: int


class InboundOrderCreateOrUpdateSchema(Schema):
    external_code: str | None = None
    description: str | None = None
    note: str | None = None
    currency: str
    supplier_code: str
    supplier_name: str
    state: InboundOrderState | None = None
    requested_delivery_date: datetime | None = None


class ReorderItemSchema(Schema):
    new_index: int


class InboundOrderTransitionSchema(Schema):
    action: Literal["next", "cancel", "rollback"] = "next"


class InboundOrderSchema(BaseOrder):
    external_code: str | None = None
    description: str | None = None
    note: str | None = None
    currency: str
    warehouse_order_codes: list[str] = []
    requested_delivery_date: datetime | None = None
    cancelled_date: datetime | None = None
    received_date: datetime | None = None
    items: list[InboundOrderItemSchema] = Field(default_factory=list)
    state: str
    warehouse_orders: list[InboundWarehouseOrderBaseSchema] = Field(
        default_factory=list
    )
    credit_note: CreditNoteBaseSchema | None = None
    invoice: InvoiceSchema | None = None


class GetInboundOrderResponse(BaseResponse):
    data: InboundOrderSchema


class GetInboundOrdersResponse(PaginatedResponse[InboundOrderSchema]): ...


class CreateInboundOrderItemResponse(BaseResponse):
    data: InboundOrderItemSchema


class OutboundOrderItemCreateSchema(Schema):
    product_code: str
    product_name: str
    amount: Annotated[float, Field(gt=0, lt=1_000_000)]
    total_price: Annotated[float, Field(ge=0, lt=100_000_000)]
    unit_price: float | None = None
    index: int | None = None
    desired_package_type_name: str | None = None
    desired_batch_code: str | None = None
    note: str | None = None


class OutboundOrderItemPricingDetailsSchema(Schema):
    base_price: float
    avg_purchase_price: float
    suggested_unit_price: float
    selected_unit_price: float
    discount_percent: float
    reason: str
    source: str
    margin_amount: float
    margin_percent: float


class OutboundOrderItemSchema(BaseSchema):
    product: ProductSchema
    amount: float
    unit_price: float
    total_price: float
    index: int
    desired_package_type_name: str | None = None
    desired_batch_code: str | None = None
    note: str | None = None
    pricing_details: OutboundOrderItemPricingDetailsSchema | None = None


class OutboundDocumentCreateOrUpdateSchema(Schema):
    """Header of an outbound order or calculation (both are written the same way)."""

    external_code: str | None = None
    description: str | None = None
    note: str | None = None
    currency: str
    customer_code: str
    customer_name: str
    # must be a (non-deleted) contact of `customer_code`; null = not specified
    contact_id: int | None = None
    requested_delivery_date: datetime | None = None


class OutboundOrderCreateOrUpdateSchema(OutboundDocumentCreateOrUpdateSchema):
    state: OutboundOrderState | None = None


class OutboundCalculationCreateOrUpdateSchema(OutboundDocumentCreateOrUpdateSchema): ...


class OutboundOrderTransitionSchema(Schema):
    action: Literal["next", "cancel"] = "next"


class OutboundCalculationTransitionSchema(Schema):
    action: Literal["close", "reopen"]


class OutboundDocumentSchema(BaseOrder):
    """Read model shared by outbound orders and calculations."""

    contact: ContactPersonSchema | None = None
    external_code: str | None = None
    description: str | None = None
    note: str | None = None
    currency: str
    requested_delivery_date: datetime | None = None
    items: list[OutboundOrderItemSchema] = Field(default_factory=list)
    state: str


class OutboundOrderSchema(OutboundDocumentSchema):
    # code of the calculation this order was created from, if any
    calculation_code: str | None = None
    warehouse_order_codes: list[str] = []
    cancelled_date: datetime | None = None
    fulfilled_date: datetime | None = None
    warehouse_orders: list[OutboundWarehouseOrderBaseSchema] = Field(
        default_factory=list
    )
    credit_note: CreditNoteBaseSchema | None = None
    invoice: InvoiceSchema | None = None


class OutboundCalculationSchema(OutboundDocumentSchema):
    # code of the order this calculation was flipped over to, if any
    order_code: str | None = None


class GetOutboundOrderResponse(BaseResponse):
    data: OutboundOrderSchema


class GetOutboundOrdersResponse(PaginatedResponse[OutboundOrderSchema]): ...


class CreateOutboundOrderItemResponse(BaseResponse):
    data: OutboundOrderItemSchema


class GetOutboundCalculationResponse(BaseResponse):
    data: OutboundCalculationSchema


class GetOutboundCalculationsResponse(PaginatedResponse[OutboundCalculationSchema]): ...
