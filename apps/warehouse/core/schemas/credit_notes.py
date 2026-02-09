from apps.warehouse.core.schemas.base import BaseResponse, BaseSchema, PaginatedResponse
from apps.warehouse.core.schemas.base_orders import InboundOrderBaseSchema
from apps.warehouse.core.schemas.orders import CreditNoteSupplierItemSchema
from apps.warehouse.models.orders import CreditNoteState


class CreditNoteSupplierSchema(BaseSchema):
    code: str
    order: InboundOrderBaseSchema
    reason: str | None = None
    note: str | None = None
    state: CreditNoteState
    items: list[CreditNoteSupplierItemSchema]


class GetCreditNoteToSupplierResponse(BaseResponse):
    data: CreditNoteSupplierSchema


class GetCreditNotesToSupplierResponse(PaginatedResponse[CreditNoteSupplierSchema]): ...
