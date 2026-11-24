from ninja import Schema

from apps.warehouse.core.schemas.base import Response
from apps.warehouse.models.document_template import DocumentTarget


class DocumentTargetSchema(Schema):
    target: DocumentTarget
    label: str
    # True when the built-in default is used (nothing customised/saved)
    is_default: bool


class LegendEntrySchema(Schema):
    """One variable available in the template context."""

    path: str
    type: str
    description: str | None = None


class LegendFilterSchema(Schema):
    name: str
    signature: str
    description: str


class DocumentLegendSchema(Schema):
    fields: list[LegendEntrySchema]
    filters: list[LegendFilterSchema]


class DocumentTemplateSchema(Schema):
    target: DocumentTarget
    label: str
    content: str
    is_default: bool
    legend: DocumentLegendSchema


class DocumentTemplateUpdateSchema(Schema):
    content: str


class DocumentRecordSchema(Schema):
    code: str
    label: str


class DocumentRenderSchema(Schema):
    """Render request: the (possibly unsaved) template over a real record."""

    record_code: str
    content: str | None = None  # None => the saved template


class TemplateErrorSchema(Schema):
    message: str
    line: int | None = None


class DocumentPreviewSchema(Schema):
    # exactly one of them is set
    html: str | None = None
    error: TemplateErrorSchema | None = None


class GetDocumentTargetsResponse(Response[list[DocumentTargetSchema]]): ...


class GetDocumentTemplateResponse(Response[DocumentTemplateSchema]): ...


class GetDocumentRecordsResponse(Response[list[DocumentRecordSchema]]): ...


class GetDocumentPreviewResponse(Response[DocumentPreviewSchema]): ...
