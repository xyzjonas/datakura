from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from ninja import Query, Router

from apps.warehouse.core.auth import superuser_auth
from apps.warehouse.core.schemas.document_templates import (
    DocumentRenderSchema,
    DocumentTemplateUpdateSchema,
    GetDocumentPreviewResponse,
    GetDocumentRecordsResponse,
    GetDocumentTargetsResponse,
    GetDocumentTemplateResponse,
)
from apps.warehouse.core.services.document_templates import document_template_service
from apps.warehouse.models.document_template import DocumentTarget

# layout of the company's documents - superusers only
routes = Router(tags=["document-templates"], auth=superuser_auth)


@routes.get("", response={200: GetDocumentTargetsResponse})
def get_document_targets(request: HttpRequest):
    return GetDocumentTargetsResponse(data=document_template_service.list_targets())


@routes.get("/{target}", response={200: GetDocumentTemplateResponse})
def get_document_template(request: HttpRequest, target: DocumentTarget):
    return GetDocumentTemplateResponse(
        data=document_template_service.get_template(target)
    )


@routes.put("/{target}", response={200: GetDocumentTemplateResponse})
def update_document_template(
    request: HttpRequest, target: DocumentTarget, body: DocumentTemplateUpdateSchema
):
    return GetDocumentTemplateResponse(
        data=document_template_service.save_template(target, body.layout)
    )


@routes.delete("/{target}", response={200: GetDocumentTemplateResponse})
def reset_document_template(request: HttpRequest, target: DocumentTarget):
    """Drops the customised layout - the built-in default is used again."""
    return GetDocumentTemplateResponse(
        data=document_template_service.reset_template(target)
    )


@routes.get("/{target}/records", response={200: GetDocumentRecordsResponse})
def get_document_records(
    request: HttpRequest, target: DocumentTarget, q: Query[str | None] = None
):
    return GetDocumentRecordsResponse(
        data=document_template_service.list_records(target, q)
    )


@routes.post("/{target}/preview", response={200: GetDocumentPreviewResponse})
def preview_document(
    request: HttpRequest, target: DocumentTarget, body: DocumentRenderSchema
):
    """HTML of a (draft) layout over a real record."""
    return GetDocumentPreviewResponse(
        data=document_template_service.render_record_html(
            target, body.record_code, body.layout
        )
    )


@routes.post("/{target}/pdf")
def export_document_pdf(
    request: HttpRequest, target: DocumentTarget, body: DocumentRenderSchema
):
    pdf = document_template_service.render_record_pdf(
        target, body.record_code, body.layout
    )
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{body.record_code}.pdf"'
    return response
