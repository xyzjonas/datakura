from apps.warehouse.core.schemas.base import BaseResponse, PaginatedResponse
from apps.warehouse.core.schemas.base_orders import CreditNoteBaseSchema, BaseOrder


class CreditNoteSupplierSchema(CreditNoteBaseSchema):
    order: BaseOrder


class GetCreditNoteToSupplierResponse(BaseResponse):
    data: CreditNoteSupplierSchema


class GetCreditNotesToSupplierResponse(PaginatedResponse[CreditNoteSupplierSchema]): ...
