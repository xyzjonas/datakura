from apps.warehouse.core.schemas.base import BaseResponse, PaginatedResponse
from apps.warehouse.core.schemas.base_orders import (
    InboundOrderBaseSchema,
    CreditNoteBaseSchema,
)


class CreditNoteSupplierSchema(CreditNoteBaseSchema):
    order: InboundOrderBaseSchema


class GetCreditNoteToSupplierResponse(BaseResponse):
    data: CreditNoteSupplierSchema


class GetCreditNotesToSupplierResponse(PaginatedResponse[CreditNoteSupplierSchema]): ...
