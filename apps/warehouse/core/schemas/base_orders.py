from datetime import datetime

from apps.warehouse.core.schemas.base import BaseSchema
from apps.warehouse.core.schemas.customer import CustomerSchema
from apps.warehouse.core.schemas.product import ProductSchema


class CreditNoteSupplierItemSchema(BaseSchema):
    product: ProductSchema
    amount: float
    unit_price: float


class InboundOrderBaseSchema(BaseSchema):
    code: str
    external_code: str | None = None
    description: str | None = None
    note: str | None = None
    supplier: CustomerSchema
    currency: str
    state: str
    warehouse_order_codes: list[str] = []
    requested_delivery_date: datetime | None = None
    cancelled_date: datetime | None = None
    received_date: datetime | None = None


class InboundWarehouseOrderBaseSchema(BaseSchema):
    code: str
    order_code: str
    state: str
    parent_order: "InboundWarehouseOrderBaseSchema | None" = None
    child_orders: list["InboundWarehouseOrderBaseSchema"] = []


class OutboundOrderBaseSchema(BaseSchema):
    code: str
    external_code: str | None = None
    description: str | None = None
    note: str | None = None
    customer: CustomerSchema
    currency: str
    state: str
    warehouse_order_codes: list[str] = []
    requested_delivery_date: datetime | None = None
    cancelled_date: datetime | None = None
    fulfilled_date: datetime | None = None


class OutboundWarehouseOrderBaseSchema(BaseSchema):
    code: str
    order_code: str
    state: str
    parent_order: "OutboundWarehouseOrderBaseSchema | None" = None
    child_orders: list["OutboundWarehouseOrderBaseSchema"] = []


class CreditNoteBaseSchema(BaseSchema):
    code: str
    reason: str | None = None
    note: str | None = None
    state: str
    items: list[CreditNoteSupplierItemSchema]
