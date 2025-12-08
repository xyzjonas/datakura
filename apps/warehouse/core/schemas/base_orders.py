from apps.warehouse.core.schemas.base import BaseSchema
from apps.warehouse.core.schemas.customer import CustomerSchema
from apps.warehouse.models.orders import InboundOrderState
from apps.warehouse.models.warehouse import InboundWarehouseOrderState


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
