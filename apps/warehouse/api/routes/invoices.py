from typing import cast

from django.db.models import QuerySet
from django.core.files.uploadedfile import UploadedFile as DjangoUploadedFile
from django.http import HttpRequest, HttpResponse
from ninja import File, Form, Router
from ninja.files import UploadedFile
from ninja.pagination import paginate

from apps.warehouse.api.pagination import InvoicesPagination
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.invoice import (
    GetInvoiceResponse,
    InvoiceMarkPaidSchema,
    InvoiceSchema,
    InvoiceStoreSchema,
    OutboundInvoiceCreateSchema,
)
from apps.warehouse.core.services.invoices import invoice_service
from apps.warehouse.models.orders import Invoice

routes = Router(tags=["invoice"])


@routes.get("/outbound", response={200: list[InvoiceSchema]})
@paginate(InvoicesPagination)
def get_outbound_invoices(request: HttpRequest):
    qs = cast(QuerySet[Invoice], invoice_service.get_outbound_invoices())
    return qs.all()


@routes.get("/inbound", response={200: list[InvoiceSchema]})
@paginate(InvoicesPagination)
def get_inbound_invoices(request: HttpRequest):
    qs = cast(QuerySet[Invoice], invoice_service.get_inbound_invoices())
    return qs.all()


@routes.post("/outbound", response={200: GetInvoiceResponse})
def create_outbound_invoice(
    request: HttpRequest,
    body: OutboundInvoiceCreateSchema,
):
    invoice = invoice_service.create_outbound_invoice(
        body,
        context=RequestContext.from_django_request(request),
    )
    return GetInvoiceResponse(data=invoice)


@routes.get("/{invoice_code}", response={200: GetInvoiceResponse})
def get_invoice(request: HttpRequest, invoice_code: str):
    return GetInvoiceResponse(data=invoice_service.get_invoice(invoice_code))


@routes.put("/{invoice_code}", response={200: GetInvoiceResponse})
def update_invoice(
    request: HttpRequest,
    invoice_code: str,
    body: Form[InvoiceStoreSchema],
    invoice_file: File[UploadedFile] | None = None,
):
    resolved_invoice_file = invoice_file or cast(
        DjangoUploadedFile | None, request.FILES.get("invoice_file")
    )

    invoice = invoice_service.update_invoice(
        invoice_code,
        body,
        context=RequestContext.from_django_request(request),
        invoice_file=resolved_invoice_file,
    )
    return GetInvoiceResponse(data=invoice)


@routes.post("/{invoice_code}/mark-paid", response={200: GetInvoiceResponse})
def mark_invoice_paid(
    request: HttpRequest,
    invoice_code: str,
    body: InvoiceMarkPaidSchema,
):
    invoice = invoice_service.mark_invoice_paid(
        invoice_code,
        context=RequestContext.from_django_request(request),
        paid_date=body.paid_date,
    )
    return GetInvoiceResponse(data=invoice)


@routes.get("/{invoice_code}/pdf")
def get_invoice_pdf(request: HttpRequest, invoice_code: str):
    response = HttpResponse(
        invoice_service.get_pdf(invoice_code), content_type="application/pdf"
    )
    response["Content-Disposition"] = f'attachment; filename="{invoice_code}.pdf"'
    return response


@routes.get("/{invoice_code}/html")
def get_invoice_html(request: HttpRequest, invoice_code: str):
    return HttpResponse(
        invoice_service.get_html(invoice_code),
        content_type="text/html",
    )
