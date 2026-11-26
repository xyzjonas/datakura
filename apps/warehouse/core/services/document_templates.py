"""Customisable layouts of the printed documents: storage, validation and rendering.

There is a single base template (`templates/documents/layout.html`) with fixed slots -
header, supplier, customer, items table and footer. A saved layout only chooses
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
    LayoutPartSchema,
    PaginationSchema,
    PartyBlockSchema,
)
from apps.warehouse.core.services import barcode_svg, document_fonts
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
LOGO_KEY = "logo"


def _party_fields() -> list[LayoutFieldSchema]:
    return [
        LayoutFieldSchema(key="name", show_label=False, bold=True, font_size=13),
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
        header=HeaderBlockSchema(
            title=d["title"],
            left=[
                LayoutFieldSchema(
                    key="code", show_label=False, bold=True, font_size=15
                ),
                LayoutFieldSchema(key="code", show_label=False, barcode=True),
            ],
            right=[
                ref.model_copy(update={"bold": True})
                for ref in _with_default_labels(spec, "header", d["header"])
            ],
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


def _migrate_field(field: dict[str, Any]) -> dict[str, Any]:
    """Composites used to list attribute keys and carry one barcode flag."""
    parts = field.get("parts")
    if parts and isinstance(parts[0], str):
        barcode = field.get("barcode", False)
        field = {
            **field,
            "barcode": False,
            "parts": [
                {"key": key, "show_label": False, "barcode": barcode} for key in parts
            ],
        }
    return field


_LOGO_ALIGN_SECTION = {"left": "left", "center": "middle", "right": "right"}


def _migrate_logo_block(raw: dict[str, Any]) -> dict[str, Any]:
    """The logo used to be a block above the header, now it is an attribute."""
    legacy = raw.pop("logo", None)
    if not isinstance(legacy, dict) or not legacy.get("image"):
        return raw
    raw["page"] = {**(raw.get("page") or {}), "logo": legacy["image"]}
    if legacy.get("enabled"):
        header = dict(raw.get("header") or {})
        section = _LOGO_ALIGN_SECTION.get(legacy.get("align", "left"), "left")
        header[section] = [
            {"key": LOGO_KEY, "show_label": False},
            *header.get(section, []),
        ]
        raw["header"] = header
    return raw


def _migrate_saved_layout(raw: dict[str, Any]) -> dict[str, Any]:
    """Layouts saved by earlier versions: header without sections, string-part composites."""
    raw = _migrate_logo_block(dict(raw))
    header = raw.get("header")
    if isinstance(header, dict):
        header = dict(header)
        if "fields" in header:
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
        for section in ("left", "middle", "right"):
            header[section] = [_migrate_field(f) for f in header.get(section, [])]
        raw["header"] = header
    for block in ("supplier", "customer"):
        if isinstance(raw.get(block), dict):
            raw[block] = {
                **raw[block],
                "fields": [_migrate_field(f) for f in raw[block].get("fields", [])],
            }
    items = raw.get("items")
    if isinstance(items, dict):
        raw["items"] = {
            **items,
            **{
                name: [_migrate_field(f) for f in items.get(name, [])]
                for name in ("columns", "summaries")
            },
        }
    return raw


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


def _leaf_text(
    leaf: LayoutPartSchema,
    defs: dict[str, FieldDef],
    values: dict[str, Any],
    currency: str | None,
) -> str:
    if leaf.text:
        return leaf.text
    return format_value(values.get(leaf.key), defs[leaf.key].kind, currency)


def _style(ref: LayoutPartSchema | LayoutFieldSchema) -> dict[str, Any]:
    return {"size": ref.font_size, "bold": ref.bold, "muted": ref.muted}


def _value(
    ref: LayoutFieldSchema,
    defs: dict[str, FieldDef],
    values: dict[str, Any],
    currency: str | None,
) -> dict[str, Any] | None:
    """The printable value of an attribute (or composite); None when all is empty."""
    parts = []
    for leaf in ref.leaves:
        text = _leaf_text(leaf, defs, values, currency)
        if text:
            is_logo = not leaf.text and leaf.key == LOGO_KEY
            # a text that cannot be a barcode is printed as text (never a logo)
            barcode = (
                barcode_svg.to_data_uri(text) if leaf.barcode and not is_logo else None
            )
            parts.append(
                {
                    "text": "" if is_logo else text,
                    "image": text if is_logo else None,
                    "barcode": barcode,
                    "barcode_text": barcode is not None and leaf.barcode_text,
                    **_style(leaf),
                }
            )
    if not parts:
        return None
    return {
        "parts": parts,
        "direction": ref.direction,
        "separator": ref.separator,
        "right": _is_right_aligned(ref, defs),
        **(_style(ref) if ref.is_composite else {}),
    }


def _is_right_aligned(ref: LayoutFieldSchema, defs: dict[str, FieldDef]) -> bool:
    return all(
        not leaf.text and defs[leaf.key].kind in RIGHT_ALIGNED for leaf in ref.leaves
    )


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
                item_columns=_catalog(list(spec.fields_of("items").values())),
                summaries=_catalog(list(spec.fields_of("summaries").values())),
                fonts=[
                    CatalogFieldSchema(key=f.key, label=f.label)
                    for f in document_fonts.FONTS.values()
                ],
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
            unknown = [
                leaf.key
                for ref in refs
                for leaf in ref.leaves
                if leaf.key and leaf.key not in known
            ]
            if unknown:
                raise InvalidDocumentLayoutError(
                    f"Unknown attribute(s) in '{name}': {', '.join(unknown)}"
                )
        if layout.items.enabled and not layout.items.columns:
            raise InvalidDocumentLayoutError("The items table needs at least 1 column")

    # -- rendering

    @staticmethod
    def _context(
        spec: DocumentSpec, layout: DocumentLayoutSchema, data: DocumentData
    ) -> dict[str, Any]:
        currency = data.currency
        header_defs = spec.fields_of("header")
        item_defs = spec.fields_of("items")
        summary_defs = spec.fields_of("summaries")
        # evaluated per print / the same for every block
        printed = {"printed_at": timezone.now(), LOGO_KEY: layout.page.logo}
        header_values = {**data.header, "code": data.code, **printed}

        parties = []
        for block, values, defs in (
            (layout.supplier, data.supplier, spec.fields_of("supplier")),
            (layout.customer, data.customer, spec.fields_of("customer")),
        ):
            if block.enabled:
                parties.append(
                    {
                        "title": block.title,
                        "rows": _rows(
                            block.fields, defs, {**(values or {}), **printed}, None
                        ),
                    }
                )

        items = None
        if layout.items.enabled:
            columns = [
                {
                    "label": _caption_of(c),
                    "right": _is_right_aligned(c, item_defs),
                }
                for c in layout.items.columns
            ]
            rows = [
                [
                    _value(c, item_defs, {**item, **printed}, currency)
                    or {"parts": [], "right": column["right"]}
                    for c, column in zip(layout.items.columns, columns, strict=True)
                ]
                for item in data.items
            ]
            items = {
                "columns": columns,
                "rows": rows,
                "summaries": _rows(
                    layout.items.summaries,
                    summary_defs,
                    {**data.summaries, **printed},
                    currency,
                ),
            }

        header = layout.header
        font = document_fonts.resolve(layout.page.font)
        return {
            "code": data.code,
            "margin": layout.page,
            "font_family": font.stack,
            "font_faces": document_fonts.font_face_css(font.key),
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
