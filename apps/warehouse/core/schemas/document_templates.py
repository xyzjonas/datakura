import re
from typing import Annotated, Literal

from ninja import Schema
from pydantic import Field, field_validator, model_validator

from apps.warehouse.core.schemas.base import Response
from apps.warehouse.models.document_template import DocumentTarget

MAX_LOGO_LENGTH = 700_000  # chars of the base64 data URL
_LOGO_RE = re.compile(r"^data:image/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+$")

Label = Annotated[str, Field(max_length=100)]


FontSize = Annotated[int, Field(ge=6, le=72)]


class _FieldBase(Schema):
    """What can be set on every printed value (single, static text or a composite part).

    `key` names a catalog attribute, `text` is a static text. `label` is the caption,
    hidden when `show_label` is off (or empty). `barcode` prints the value as a Code 128
    barcode, `barcode_text` adds the plain value under it. `font_size` (px) scales the
    text and the barcode alike; empty = the surrounding size.
    """

    key: str = ""
    text: Annotated[str, Field(max_length=200)] = ""
    label: Label = ""
    show_label: bool = True
    barcode: bool = False
    barcode_text: bool = False
    font_size: FontSize | None = None
    bold: bool = False
    muted: bool = False


class LayoutPartSchema(_FieldBase):
    """A single attribute or a static text - also the building block of a composite."""

    @model_validator(mode="after")
    def _key_or_text(self) -> "LayoutPartSchema":
        if bool(self.key) == bool(self.text):
            raise ValueError("A value is either an attribute (key) or a static text")
        return self


class LayoutFieldSchema(_FieldBase):
    """One printed line: a single attribute, a static text or a composite.

    Composite: `parts` are chained (`direction` row = one line joined by `separator`,
    column = one under another); each part has all the options of a single attribute.
    The options set on the composite itself are the defaults of its parts (size, bold,
    muted) and its caption - the barcode is chosen per part.
    """

    parts: list[LayoutPartSchema] = Field(default_factory=list, max_length=10)
    direction: Literal["row", "column"] = "row"
    separator: Annotated[str, Field(max_length=10)] = ", "

    @property
    def is_composite(self) -> bool:
        return bool(self.parts)

    @property
    def leaves(self) -> list[LayoutPartSchema]:
        if self.parts:
            return self.parts
        return [LayoutPartSchema.model_validate(self.model_dump(exclude={"parts"}))]

    @model_validator(mode="after")
    def _single_or_composite(self) -> "LayoutFieldSchema":
        if self.parts:
            if self.key or self.text or self.barcode or self.barcode_text:
                raise ValueError("A composite has no key, text or barcode of its own")
        elif bool(self.key) == bool(self.text):
            raise ValueError("A value is either an attribute (key) or a static text")
        return self


class LogoBlockSchema(Schema):
    enabled: bool = False
    # PNG / JPEG / GIF / WebP as a base64 data URL (nothing is fetched while printing)
    image: str | None = None
    align: Literal["left", "center", "right"] = "left"

    @field_validator("image")
    @classmethod
    def _image_is_small_data_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) > MAX_LOGO_LENGTH:
            raise ValueError("Logo is too large")
        if not _LOGO_RE.match(value):
            raise ValueError("Logo must be a PNG, JPEG, GIF or WebP image")
        return value


class HeaderBlockSchema(Schema):
    title: Label = ""
    # three sections side by side, each a list of attributes (one per line)
    left: list[LayoutFieldSchema] = Field(default_factory=list, max_length=20)
    middle: list[LayoutFieldSchema] = Field(default_factory=list, max_length=20)
    right: list[LayoutFieldSchema] = Field(default_factory=list, max_length=20)


class PaginationSchema(Schema):
    """Page number printed in a corner of every page of the PDF."""

    enabled: bool = False
    position: Literal[
        "top-left",
        "top-center",
        "top-right",
        "bottom-left",
        "bottom-center",
        "bottom-right",
    ] = "bottom-right"


class PartyBlockSchema(Schema):
    enabled: bool = True
    title: Label = ""
    fields: list[LayoutFieldSchema] = Field(default_factory=list, max_length=20)


class ItemsBlockSchema(Schema):
    enabled: bool = True
    columns: list[LayoutFieldSchema] = Field(default_factory=list, max_length=12)
    summaries: list[LayoutFieldSchema] = Field(default_factory=list, max_length=10)


class PageSchema(Schema):
    """Page margins in px (0 = no margin)."""

    margin_top: Annotated[int, Field(ge=0, le=200)] = 60
    margin_right: Annotated[int, Field(ge=0, le=200)] = 53
    margin_bottom: Annotated[int, Field(ge=0, le=200)] = 60
    margin_left: Annotated[int, Field(ge=0, le=200)] = 53


class FooterBlockSchema(Schema):
    enabled: bool = False
    text: Annotated[str, Field(max_length=1000)] = ""


class DocumentLayoutSchema(Schema):
    """The customisable parts of a document - the base template places them."""

    logo: LogoBlockSchema = Field(default_factory=LogoBlockSchema)
    header: HeaderBlockSchema = Field(default_factory=HeaderBlockSchema)
    customer: PartyBlockSchema = Field(default_factory=PartyBlockSchema)
    supplier: PartyBlockSchema = Field(default_factory=PartyBlockSchema)
    items: ItemsBlockSchema = Field(default_factory=ItemsBlockSchema)
    footer: FooterBlockSchema = Field(default_factory=FooterBlockSchema)
    pagination: PaginationSchema = Field(default_factory=PaginationSchema)
    page: PageSchema = Field(default_factory=PageSchema)


class CatalogFieldSchema(Schema):
    """An attribute the admin may pick, with its default caption."""

    key: str
    label: str


class DocumentCatalogSchema(Schema):
    """Attributes available per block of one document kind."""

    header_fields: list[CatalogFieldSchema]
    supplier_fields: list[CatalogFieldSchema]
    # supplier's + the selected contact person's (only where the document has one)
    customer_fields: list[CatalogFieldSchema]
    item_columns: list[CatalogFieldSchema]
    summaries: list[CatalogFieldSchema]


class DocumentTargetSchema(Schema):
    target: DocumentTarget
    label: str
    # True when the built-in default layout is used (nothing saved)
    is_default: bool


class DocumentTemplateSchema(Schema):
    target: DocumentTarget
    label: str
    layout: DocumentLayoutSchema
    is_default: bool
    catalog: DocumentCatalogSchema


class DocumentTemplateUpdateSchema(Schema):
    layout: DocumentLayoutSchema


class DocumentRecordSchema(Schema):
    code: str
    label: str


class DocumentRenderSchema(Schema):
    """Render request: the (possibly unsaved) layout over a real record."""

    record_code: str
    layout: DocumentLayoutSchema | None = None  # None => the saved layout


class GetDocumentTargetsResponse(Response[list[DocumentTargetSchema]]): ...


class GetDocumentTemplateResponse(Response[DocumentTemplateSchema]): ...


class GetDocumentRecordsResponse(Response[list[DocumentRecordSchema]]): ...


class GetDocumentPreviewResponse(Response[str]): ...
