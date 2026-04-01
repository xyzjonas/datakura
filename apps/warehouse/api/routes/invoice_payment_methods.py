from __future__ import annotations

from typing import cast

from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import InvoicePaymentMethodPagination
from apps.warehouse.core.schemas.base import EmptyResponse
from apps.warehouse.core.schemas.invoice import (
    GetInvoicePaymentMethodResponse,
    InvoicePaymentMethodCreateOrUpdateSchema,
    InvoicePaymentMethodSchema,
)
from apps.warehouse.core.transformation import invoice_payment_method_orm_to_schema
from apps.warehouse.models.orders import InvoicePaymentMethod

routes = Router(tags=["invoice_payment_method"])


@routes.get("", response={200: list[InvoicePaymentMethodSchema]})
@paginate(InvoicePaymentMethodPagination)
def get_invoice_payment_methods(request: HttpRequest, search_term: str | None = None):
    qs = cast(QuerySet[InvoicePaymentMethod], InvoicePaymentMethod.objects.all())
    if search_term:
        qs = qs.filter(name__icontains=search_term.lower())

    return qs.all()


@routes.post("", response={200: GetInvoicePaymentMethodResponse})
def create_invoice_payment_method(
    request: HttpRequest,
    body: InvoicePaymentMethodCreateOrUpdateSchema,
):
    payment_method, _ = InvoicePaymentMethod.objects.get_or_create(name=body.name)
    return GetInvoicePaymentMethodResponse(
        data=invoice_payment_method_orm_to_schema(payment_method)
    )


@routes.put("/{method_id}", response={200: GetInvoicePaymentMethodResponse})
def update_invoice_payment_method(
    request: HttpRequest,
    method_id: int,
    body: InvoicePaymentMethodCreateOrUpdateSchema,
):
    payment_method = InvoicePaymentMethod.objects.get(pk=method_id)
    payment_method.name = body.name
    payment_method.save()
    return GetInvoicePaymentMethodResponse(
        data=invoice_payment_method_orm_to_schema(payment_method)
    )


@routes.delete("/{method_id}", response={200: EmptyResponse})
def delete_invoice_payment_method(request: HttpRequest, method_id: int):
    InvoicePaymentMethod.objects.get(pk=method_id).delete()
    return EmptyResponse(success=True)
