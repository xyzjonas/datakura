from typing import cast

from django.db.models import Q
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from ninja.pagination import paginate
from ninja.router import Router

from apps.warehouse.api.pagination import CreditNoteToSupplierPagination
from apps.warehouse.core.schemas.credit_notes import (
    GetCreditNoteToSupplierResponse,
    CreditNoteSupplierSchema,
)
from apps.warehouse.core.transformation import credit_note_supplier_orm_to_schema
from apps.warehouse.models.orders import CreditNoteToSupplier

routes = Router(tags=["inbound_order"])


@routes.get("", response={200: list[CreditNoteSupplierSchema]})
@paginate(CreditNoteToSupplierPagination)
def get_credit_notes_to_supplier(request: HttpRequest, search_term: str | None = None):
    """
    List credit notes for incoming goods (towards supplier)
    """
    qs = cast(
        QuerySet[CreditNoteToSupplier],
        CreditNoteToSupplier.objects.select_related("order", "order__supplier"),
    )
    if search_term:
        search_term = search_term.lower()
        qs = qs.filter(
            Q(code__iexact=search_term)
            | Q(code__icontains=search_term)
            | Q(order__supplier__name__icontains=search_term)
        )

    return qs.all()


@routes.get("/{note_code}", response={200: GetCreditNoteToSupplierResponse})
def get_credit_note_to_supplier(request: HttpRequest, note_code: str):
    """
    Retrieve a single credit note.
    """
    return GetCreditNoteToSupplierResponse(
        data=credit_note_supplier_orm_to_schema(
            CreditNoteToSupplier.objects.get(code=note_code)
        )
    )
