"""Customisable layouts of the printed documents: storage, validation and rendering.

There is a single base template (`templates/documents/layout.html`) with fixed slots -
logo, header, supplier, customer, items table and footer. A saved layout only chooses
what is printed inside them (which attributes, in which order, with which captions).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.template.defaultfilters import floatformat
from django.template.loader import render_to_string
from django.utils import dateformat, timezone

from apps.warehouse.core.exceptions import (
    InvalidDocumentLayoutError,
    NotFoundException,
)
from apps.warehouse.core.schemas.document_templates import (
    CatalogFieldSchema,
    DocumentCatalogSchema,
    DocumentLayoutSchema,
    DocumentRecordSchema,
    DocumentTargetSchema,
    DocumentTemplateSchema,
    FooterBlockSchema,
    HeaderBlockSchema,
    ItemsBlockSchema,
    LayoutFieldSchema,
    LogoBlockSchema,
    PaginationSchema,
    PartyBlockSchema,
)
from apps.warehouse.core.services import barcode_svg
from apps.warehouse.core.services.document_data import (
    SPECS,
    DocumentData,
    DocumentSpec,
    FieldDef,
    Kind,
)
from apps.warehouse.core.services.pdf import print_html_to_pdf
from apps.warehouse.models.document_template import DocumentTarget, DocumentTemplate

LAYOUT_TEMPLATE = "documents/layout.html"
DATE_FORMAT = "d. m. Y"
DATETIME_FORMAT = "d. m. Y H:i"
RIGHT_ALIGNED = {Kind.QUANTITY, Kind.MONEY}


def _party_fields() -> list[LayoutFieldSchema]:
    return [
        LayoutFieldSchema(key="name", show_label=False),
        LayoutFieldSchema(key="address", show_label=False),
        LayoutFieldSchema(key="identification", label="IČO:"),
        LayoutFieldSchema(key="tax_identification", label="DIČ:"),
    ]


def _caption(spec: DocumentSpec, block: str, key: str) -> str:
    return spec.fields_of(block)[key].label


def _with_default_labels(
    spec: DocumentSpec, block: str, keys: list[str]
) -> list[LayoutFieldSchema]:
    return [LayoutFieldSchema(key=k, label=_caption(spec, block, k)) for k in keys]


_DEFAULTS: dict[DocumentTarget, dict[str, Any]] = {
    DocumentTarget.OUTBOUND_INVOICE: {
        "title": "Faktura",
        "header": ["issued_date", "due_date", "taxable_supply_date", "payment_method"],
        "items": [
            "product_code",
            "product_name",
            "amount",
            "unit_price",
            "total_price",
        ],
        "summaries": ["total_amount"],
        "supplier": "Dodavatel",
        "customer": "Odběratel",
    },
    DocumentTarget.DELIVERY_NOTE: {
        "title": "Dodací list",
        "header": ["created", "requested_delivery_date", "external_code"],
        "items": ["product_code", "product_name", "amount", "unit"],
        "summaries": ["items_count"],
        "supplier": "Dodavatel",
        "customer": "Odběratel",
    },
    DocumentTarget.OFFER: {
        "title": "Nabídka",
        "header": ["created", "requested_delivery_date", "contact"],
        "items": [
            "product_code",
            "product_name",
            "amount",
            "unit_price",
            "total_price",
        ],
        "summaries": ["total_amount"],
        "supplier": "Dodavatel",
        "customer": "Zákazník",
    },
    DocumentTarget.ISSUE_NOTE: {
        "title": "Výdejka",
        "header": ["order_code", "created"],
        "items": ["index", "product_code", "product_name", "amount", "unit"],
        "summaries": ["items_count"],
        "supplier": "Dodavatel",
        "customer": "Odběratel",
    },
    DocumentTarget.GOODS_RECEIPT: {
        "title": "Příjemka",
        "header": ["order_code", "created"],
        "items": [
            "index",
            "product_code",
            "product_name",
            "amount",
            "unit",
            "total_price",
        ],
        "summaries": ["total_amount"],
        "supplier": "Dodavatel",
        "customer": "Odběratel",
    },
}


def default_layout(target: DocumentTarget) -> DocumentLayoutSchema:
    spec = _spec(target)
    d = _DEFAULTS[spec.target]
    return DocumentLayoutSchema(
        logo=LogoBlockSchema(),
        header=HeaderBlockSchema(
            title=d["title"],
            left=[
                LayoutFieldSchema(key="code", show_label=False),
                LayoutFieldSchema(key="code", show_label=False, barcode=True),
            ],
            right=_with_default_labels(spec, "header", d["header"]),
        ),
        supplier=PartyBlockSchema(title=d["supplier"], fields=_party_fields()),
        customer=PartyBlockSchema(title=d["customer"], fields=_party_fields()),
        items=ItemsBlockSchema(
            columns=_with_default_labels(spec, "items", d["items"]),
            summaries=_with_default_labels(spec, "summaries", d["summaries"]),
        ),
        footer=FooterBlockSchema(),
        pagination=PaginationSchema(),
    )


def _migrate_saved_layout(raw: dict[str, Any]) -> dict[str, Any]:
    """Layouts saved before the header had sections: one list + a barcode toggle."""
    header = raw.get("header")
    if not isinstance(header, dict) or "fields" not in header:
        return raw
    header = dict(header)
    legacy = header.pop("fields")
    show_barcode = header.pop("show_barcode", True)
    header.setdefault("right", legacy)
    header.setdefault(
        "left",
        [
            {"key": "code", "show_label": False},
            *(
                [{"key": "code", "show_label": False, "barcode": True}]
                if show_barcode
                else []
            ),
        ],
    )
    return {**raw, "header": header}


def _spec(target: DocumentTarget | str) -> DocumentSpec:
    try:
        return SPECS[DocumentTarget(target)]
    except (KeyError, ValueError) as e:
        raise NotFoundException(f"Unknown document target '{target}'") from e


def _catalog(fields: list[FieldDef]) -> list[CatalogFieldSchema]:
    return [CatalogFieldSchema(key=f.key, label=f.label) for f in fields]


# --- value formatting --------------------------------------------------------------


def format_value(value: Any, kind: Kind, currency: str | None = None) -> str:
    if value is None or value == "":
        return ""
    if kind in (Kind.DATE, Kind.DATETIME) and isinstance(value, (date, datetime)):
        if isinstance(value, datetime) and timezone.is_aware(value):
            value = timezone.localtime(value)
        if kind is Kind.DATE or not isinstance(value, datetime):
            return dateformat.format(value, DATE_FORMAT)
        return dateformat.format(value, DATETIME_FORMAT)
    if kind is Kind.QUANTITY:
        # no trailing zeros: 3.5000 -> 3.5
        number = Decimal(str(value)).normalize()
        return floatformat(number, min(4, max(0, -number.as_tuple().exponent)))  # type: ignore[operator]
    if kind is Kind.MONEY:
        text = floatformat(value, 2)
        return f"{text} {currency}" if currency else text
    return str(value)


def _value(
    ref: LayoutFieldSchema,
    defs: dict[str, FieldDef],
    values: dict[str, Any],
    currency: str | None,
) -> dict[str, Any] | None:
    """The printable value of an attribute (or composite); None when all is empty."""
    parts = []
    for key in ref.keys:
        text = format_value(values.get(key), defs[key].kind, currency)
        if text:
            # a text that cannot be a barcode is printed as text
            barcode = barcode_svg.to_data_uri(text) if ref.barcode else None
            parts.append({"text": text, "barcode": barcode})
    if not parts:
        return None
    return {
        "parts": parts,
        "direction": ref.direction,
        "separator": ref.separator,
        "right": all(defs[k].kind in RIGHT_ALIGNED for k in ref.keys),
    }


def _caption_of(ref: LayoutFieldSchema) -> str:
    return ref.label if ref.show_label else ""


def _rows(
    refs: list[LayoutFieldSchema],
    defs: dict[str, FieldDef],
    values: dict[str, Any],
    currency: str | None,
) -> list[dict[str, Any]]:
    """Captioned values of the attributes that are filled in."""
    rows = []
    for ref in refs:
        value = _value(ref, defs, values, currency)
        if value:
            rows.append({"label": _caption_of(ref), "value": value})
    return rows


# --- service -----------------------------------------------------------------------


class DocumentTemplateService:
    # -- storage

    @classmethod
    def get_layout(cls, target: DocumentTarget) -> tuple[DocumentLayoutSchema, bool]:
        """(layout, is the built-in default)"""
        _spec(target)
        saved = DocumentTemplate.objects.filter(target=target).first()
        if saved is None:
            return default_layout(target), True
        return DocumentLayoutSchema.model_validate(
            _migrate_saved_layout(saved.layout)
        ), False

    @classmethod
    def list_targets(cls) -> list[DocumentTargetSchema]:
        customised = set(DocumentTemplate.objects.values_list("target", flat=True))
        return [
            DocumentTargetSchema(
                target=target,
                label=DocumentTarget(target).label,
                is_default=target.value not in customised,
            )
            for target in SPECS
        ]

    @classmethod
    def get_template(cls, target: DocumentTarget) -> DocumentTemplateSchema:
        layout, is_default = cls.get_layout(target)
        spec = _spec(target)
        return DocumentTemplateSchema(
            target=target,
            label=DocumentTarget(target).label,
            layout=layout,
            is_default=is_default,
            catalog=DocumentCatalogSchema(
                header_fields=_catalog(list(spec.fields_of("header").values())),
                supplier_fields=_catalog(list(spec.fields_of("supplier").values())),
                customer_fields=_catalog(list(spec.fields_of("customer").values())),
                item_columns=_catalog(spec.item_columns),
                summaries=_catalog(spec.summaries),
            ),
        )

    @classmethod
    def save_template(
        cls, target: DocumentTarget, layout: DocumentLayoutSchema
    ) -> DocumentTemplateSchema:
        cls.validate(target, layout)
        DocumentTemplate.objects.update_or_create(
            target=target, defaults={"layout": layout.model_dump(mode="json")}
        )
        return cls.get_template(target)

    @classmethod
    def reset_template(cls, target: DocumentTarget) -> DocumentTemplateSchema:
        _spec(target)
        DocumentTemplate.objects.filter(target=target).delete()
        return cls.get_template(target)

    @classmethod
    def list_records(
        cls, target: DocumentTarget, q: str | None = None
    ) -> list[DocumentRecordSchema]:
        return _spec(target).list_records(q)

    # -- validation

    @staticmethod
    def validate(target: DocumentTarget, layout: DocumentLayoutSchema) -> None:
        """Every picked attribute (also inside a composite) must exist for the document."""
        spec = _spec(target)
        blocks = {
            "header (left)": ("header", layout.header.left),
            "header (middle)": ("header", layout.header.middle),
            "header (right)": ("header", layout.header.right),
            "supplier": ("supplier", layout.supplier.fields),
            "customer": ("customer", layout.customer.fields),
            "items": ("items", layout.items.columns),
            "summaries": ("summaries", layout.items.summaries),
        }
        for name, (block, refs) in blocks.items():
            known = spec.fields_of(block)
            unknown = [k for ref in refs for k in ref.keys if k not in known]
            if unknown:
                raise InvalidDocumentLayoutError(
                    f"Unknown attribute(s) in '{name}': {', '.join(unknown)}"
                )
        if layout.items.enabled and not layout.items.columns:
            raise InvalidDocumentLayoutError("The items table needs at least 1 column")
        if layout.logo.enabled and not layout.logo.image:
            raise InvalidDocumentLayoutError("Logo is enabled but no image is set")

    # -- rendering

    @staticmethod
    def _context(
        spec: DocumentSpec, layout: DocumentLayoutSchema, data: DocumentData
    ) -> dict[str, Any]:
        currency = data.currency
        header_defs = spec.fields_of("header")
        item_defs = spec.fields_of("items")
        summary_defs = spec.fields_of("summaries")
        header_values = {**data.header, "code": data.code}

        parties = []
        for block, values, defs in (
            (layout.supplier, data.supplier, spec.fields_of("supplier")),
            (layout.customer, data.customer, spec.fields_of("customer")),
        ):
            if block.enabled:
                parties.append(
                    {
                        "title": block.title,
                        "rows": _rows(block.fields, defs, values or {}, None),
                    }
                )

        items = None
        if layout.items.enabled:
            columns = [
                {
                    "label": _caption_of(c),
                    "right": all(item_defs[k].kind in RIGHT_ALIGNED for k in c.keys),
                }
                for c in layout.items.columns
            ]
            rows = [
                [
                    _value(c, item_defs, item, currency)
                    or {"parts": [], "right": column["right"]}
                    for c, column in zip(layout.items.columns, columns, strict=True)
                ]
                for item in data.items
            ]
            items = {
                "columns": columns,
                "rows": rows,
                "summaries": _rows(
                    layout.items.summaries, summary_defs, data.summaries, currency
                ),
            }

        logo = layout.logo
        header = layout.header
        return {
            "code": data.code,
            "logo": {"image": logo.image, "align": logo.align}
            if logo.enabled and logo.image
            else None,
            "header": {
                "title": header.title,
                "sections": [
                    {
                        "name": name,
                        "rows": _rows(refs, header_defs, header_values, currency),
                    }
                    for name, refs in (
                        ("left", header.left),
                        ("middle", header.middle),
                        ("right", header.right),
                    )
                ],
            },
            "parties": parties,
            "items": items,
            "footer": layout.footer.text
            if layout.footer.enabled and layout.footer.text.strip()
            else None,
            # "top-left" .. "bottom-right": a CSS @page margin box, only the PDF paginates
            "page_number_box": layout.pagination.position
            if layout.pagination.enabled
            else None,
        }

    @classmethod
    def render_record_html(
        cls,
        target: DocumentTarget,
        record_code: str,
        layout: DocumentLayoutSchema | None = None,
    ) -> str:
        """The document over a record; `layout` None => the saved (or default) one."""
        spec = _spec(target)
        if layout is None:
            layout, _ = cls.get_layout(target)
        else:
            cls.validate(target, layout)
        return render_to_string(
            LAYOUT_TEMPLATE, cls._context(spec, layout, spec.build(record_code))
        )

    @classmethod
    def render_record_pdf(
        cls,
        target: DocumentTarget,
        record_code: str,
        layout: DocumentLayoutSchema | None = None,
    ) -> bytes:
        return print_html_to_pdf(
            content_html=cls.render_record_html(target, record_code, layout)
        )


document_template_service = DocumentTemplateService()
