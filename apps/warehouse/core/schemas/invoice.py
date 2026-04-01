from datetime import date

from ninja import Schema

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
