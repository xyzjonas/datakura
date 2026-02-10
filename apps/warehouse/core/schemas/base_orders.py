from apps.warehouse.core.schemas.base import BaseSchema
from apps.warehouse.core.schemas.customer import CustomerSchema
from apps.warehouse.core.schemas.product import ProductSchema
from apps.warehouse.models.orders import InboundOrderState, CreditNoteState
from apps.warehouse.models.warehouse import InboundWarehouseOrderState


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
    state: InboundOrderState
    warehouse_order_code: str | None = None


class InboundWarehouseOrderBaseSchema(BaseSchema):
    code: str
    order_code: str
    state: InboundWarehouseOrderState


class CreditNoteBaseSchema(BaseSchema):
    code: str
    reason: str | None = None
    note: str | None = None
    state: CreditNoteState
    items: list[CreditNoteSupplierItemSchema]
