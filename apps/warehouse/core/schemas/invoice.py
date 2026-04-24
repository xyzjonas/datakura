from datetime import date

from ninja import Schema
from pydantic import Field

from apps.warehouse.core.schemas.base import BaseSchema, PaginatedResponse, Response
from apps.warehouse.core.schemas.base import MediaFileSchema
from apps.warehouse.core.schemas.customer import CustomerSchema


class InvoicePaymentMethodSchema(BaseSchema):
    id: int
    name: str


class InvoicePaymentMethodCreateOrUpdateSchema(Schema):
    name: str


class GetInvoicePaymentMethodResponse(Response[InvoicePaymentMethodSchema]): ...


class GetInvoicePaymentMethodsResponse(
    PaginatedResponse[InvoicePaymentMethodSchema]
): ...


class InvoiceSchema(BaseSchema):
    code: str
    customer: CustomerSchema | None = None
    supplier: CustomerSchema | None = None
    issued_date: date
    due_date: date
    payment_method: InvoicePaymentMethodSchema
    external_code: str | None = None
    taxable_supply_date: date
    paid_date: date | None = None
    currency: str
    note: str | None = None
    document: MediaFileSchema | None = None


class InvoiceStoreSchema(Schema):
    customer_code: str | None = None
    supplier_code: str | None = None
    code: str
    issued_date: date
    due_date: date
    payment_method_name: str
    external_code: str | None = None
    taxable_supply_date: date
    paid_date: date | None = None
    currency: str
    note: str | None = None


class OutboundInvoiceCreateSchema(Schema):
    order_codes: list[str] = Field(default_factory=list)
    issued_date: date
    due_date: date
    payment_method_name: str | None = None
    external_code: str | None = None
    taxable_supply_date: date
    paid_date: date | None = None
    note: str | None = None


class InvoiceMarkPaidSchema(Schema):
    paid_date: date | None = None


class InvoiceOrderProductSchema(Schema):
    code: str
    name: str
    unit: str | None = None


class InvoiceOutboundOrderItemSchema(BaseSchema):
    product: InvoiceOrderProductSchema
    amount: float
    unit_price: float
    total_price: float
    index: int


class InvoiceOutboundOrderSchema(BaseSchema):
    code: str
    external_code: str | None = None
    state: str
    currency: str
    items: list[InvoiceOutboundOrderItemSchema] = Field(default_factory=list)


class InvoiceInboundOrderItemSchema(BaseSchema):
    product: InvoiceOrderProductSchema
    amount: float
    unit_price: float
    total_price: float
    index: int


class InvoiceInboundOrderSchema(BaseSchema):
    code: str
    external_code: str | None = None
    state: str
    currency: str
    items: list[InvoiceInboundOrderItemSchema] = Field(default_factory=list)


class InvoiceDetailSchema(InvoiceSchema):
    outbound_orders: list[InvoiceOutboundOrderSchema] = Field(default_factory=list)
    inbound_orders: list[InvoiceInboundOrderSchema] = Field(default_factory=list)


class GetInvoicesResponse(PaginatedResponse[InvoiceSchema]): ...


class GetInvoiceResponse(Response[InvoiceDetailSchema]): ...
