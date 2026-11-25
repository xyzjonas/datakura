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


def _fields(*keys: str) -> list[LayoutFieldSchema]:
    return [LayoutFieldSchema(key=key) for key in keys]


def _party_fields() -> list[LayoutFieldSchema]:
    return [
        LayoutFieldSchema(key="name"),
        LayoutFieldSchema(key="address"),
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
            show_barcode=True,
            fields=_with_default_labels(spec, "header", d["header"]),
        ),
        supplier=PartyBlockSchema(title=d["supplier"], fields=_party_fields()),
        customer=PartyBlockSchema(title=d["customer"], fields=_party_fields()),
        items=ItemsBlockSchema(
            columns=_with_default_labels(spec, "items", d["items"]),
            summaries=_with_default_labels(spec, "summaries", d["summaries"]),
        ),
        footer=FooterBlockSchema(),
    )


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


def _rows(
    refs: list[LayoutFieldSchema],
    defs: dict[str, FieldDef],
    values: dict[str, Any],
    currency: str | None,
) -> list[dict[str, str]]:
    """Captioned values of the attributes that are filled in."""
    rows = []
    for ref in refs:
        value = format_value(values.get(ref.key), defs[ref.key].kind, currency)
        if value:
            rows.append({"label": ref.label, "value": value})
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
        return DocumentLayoutSchema.model_validate(saved.layout), False

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
                header_fields=_catalog(spec.header_fields),
                party_fields=_catalog(list(spec.fields_of("party").values())),
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
        """Every picked attribute must exist for the document and be picked once."""
        spec = _spec(target)
        blocks = {
            "header": ("header", layout.header.fields),
            "supplier": ("party", layout.supplier.fields),
            "customer": ("party", layout.customer.fields),
            "items": ("items", layout.items.columns),
            "summaries": ("summaries", layout.items.summaries),
        }
        for name, (block, refs) in blocks.items():
            known = spec.fields_of(block)
            keys = [ref.key for ref in refs]
            unknown = [k for k in keys if k not in known]
            if unknown:
                raise InvalidDocumentLayoutError(
                    f"Unknown attribute(s) in '{name}': {', '.join(unknown)}"
                )
            if len(set(keys)) != len(keys):
                raise InvalidDocumentLayoutError(
                    f"Attribute picked more than once in '{name}'"
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
        party_defs = spec.fields_of("party")
        item_defs = spec.fields_of("items")
        summary_defs = spec.fields_of("summaries")

        parties = []
        for block, values in (
            (layout.supplier, data.supplier),
            (layout.customer, data.customer),
        ):
            if block.enabled:
                parties.append(
                    {
                        "title": block.title,
                        "rows": _rows(block.fields, party_defs, values or {}, None),
                    }
                )

        items = None
        if layout.items.enabled:
            columns = [
                {
                    "label": c.label,
                    "right": item_defs[c.key].kind in RIGHT_ALIGNED,
                }
                for c in layout.items.columns
            ]
            rows = [
                [
                    {
                        "value": format_value(
                            item.get(c.key), item_defs[c.key].kind, currency
                        ),
                        "right": item_defs[c.key].kind in RIGHT_ALIGNED,
                    }
                    for c in layout.items.columns
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
        return {
            "code": data.code,
            "logo": {"image": logo.image, "align": logo.align}
            if logo.enabled and logo.image
            else None,
            "header": {
                "title": layout.header.title,
                "barcode": barcode_svg.to_data_uri(data.code)
                if layout.header.show_barcode
                else None,
                "rows": _rows(layout.header.fields, header_defs, data.header, currency),
            },
            "parties": parties,
            "items": items,
            "footer": layout.footer.text
            if layout.footer.enabled and layout.footer.text.strip()
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
