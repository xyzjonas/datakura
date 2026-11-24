"""Editable (Jinja2) templates of the printed documents: storage, context and rendering."""

from __future__ import annotations

import types
import typing
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from django.db.models import Q
from django.template.defaultfilters import floatformat
from django.utils import dateformat, timezone
from jinja2 import ChainableUndefined, TemplateError
from jinja2 import TemplateSyntaxError as JinjaSyntaxError
from jinja2.sandbox import SandboxedEnvironment, SecurityError
from pydantic import BaseModel

from apps.warehouse.core.exceptions import NotFoundException, TemplateRenderError
from apps.warehouse.core.schemas.document_templates import (
    DocumentLegendSchema,
    DocumentRecordSchema,
    DocumentTargetSchema,
    DocumentTemplateSchema,
    LegendEntrySchema,
    LegendFilterSchema,
)
from apps.warehouse.core.schemas.invoice import InvoiceDetailSchema
from apps.warehouse.core.schemas.orders import (
    OutboundCalculationSchema,
    OutboundOrderSchema,
)
from apps.warehouse.core.schemas.warehouse import (
    InboundWarehouseOrderSchema,
    OutboundWarehouseOrderSchema,
)
from apps.warehouse.core.services.invoices import invoice_service
from apps.warehouse.core.services.outbound_calculations import (
    outbound_calculations_service,
)
from apps.warehouse.core.services.outbound_orders import outbound_orders_service
from apps.warehouse.core.services.pdf import print_html_to_pdf
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.document_template import DocumentTarget, DocumentTemplate

DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "documents"
MAX_RECORDS = 50
DEFAULT_DATE_FORMAT = "d. m. Y"
# the filename Jinja reports for templates compiled from a string
_TEMPLATE_FILENAME = "<template>"


# --- Template filters --------------------------------------------------------------


def _parse_date(value: Any) -> date | datetime | None:
    if isinstance(value, (date, datetime)):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def date_filter(value: Any, fmt: str = DEFAULT_DATE_FORMAT) -> str:
    parsed = _parse_date(value)
    if parsed is None:
        return ""
    if isinstance(parsed, datetime) and timezone.is_aware(parsed):
        parsed = timezone.localtime(parsed)
    return dateformat.format(parsed, fmt)


def number_filter(value: Any, decimals: int = 2) -> str:
    if value is None or value == "":
        return ""
    return floatformat(value, decimals)


def money_filter(value: Any, currency: str | None = None) -> str:
    formatted = number_filter(value, 2)
    if not formatted:
        return ""
    return f"{formatted} {currency}" if currency else formatted


@dataclass(frozen=True)
class TemplateFilter:
    name: str
    signature: str
    description: str
    func: Callable[..., str]


CUSTOM_FILTERS = [
    TemplateFilter(
        "date",
        'date(fmt="d. m. Y")',
        "Formats a date / datetime (Django date format). Empty for missing values.",
        date_filter,
    ),
    TemplateFilter(
        "number",
        "number(decimals=2)",
        "Localised number with fixed decimals and thousands grouping.",
        number_filter,
    ),
    TemplateFilter(
        "money",
        "money(currency)",
        "Number with 2 decimals followed by the currency, e.g. 1 250,00 CZK.",
        money_filter,
    ),
]
# Jinja built-ins worth advertising in the legend
BUILTIN_FILTER_HELP = [
    ("default", 'default("-")', "Fallback for empty / missing values."),
    ("length", "length", "Number of items in a list."),
    ("join", 'join(", ")', "Joins the items of a list into a string."),
    ("upper", "upper", "Upper-case text."),
    ("lower", "lower", "Lower-case text."),
    ("round", "round(2)", "Rounds a number."),
    ("sum", "sum(attribute='total_price')", "Sums a list (optionally an attribute)."),
]


class _DocumentEnvironment(SandboxedEnvironment):
    """Sandbox where `a.b` prefers the *key* `b` of a dict (as Django templates do).

    Plain Jinja resolves `order.items` to the `dict.items` method, but the context is
    made of dicts with fields named like dict methods (`items`, `values`, ...).
    """

    def getattr(self, obj: Any, attribute: str) -> Any:
        if isinstance(obj, Mapping) and attribute in obj:
            return obj[attribute]
        return super().getattr(obj, attribute)

    def unsafe_undefined(self, obj: Any, attribute: str) -> Any:
        # fail loudly (the editor shows it) instead of silently rendering nothing
        raise SecurityError(
            f"access to attribute {attribute!r} of {type(obj).__name__!r} object "
            "is unsafe"
        )


def _build_environment() -> SandboxedEnvironment:
    env = _DocumentEnvironment(autoescape=True, undefined=ChainableUndefined)
    for flt in CUSTOM_FILTERS:
        env.filters[flt.name] = flt.func
    return env


_environment = _build_environment()


def _error_line(exc: BaseException) -> int | None:
    """Line of the template (not of our code) the failure happened on."""
    if isinstance(exc, JinjaSyntaxError):
        return exc.lineno
    line = None
    tb = exc.__traceback__
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == _TEMPLATE_FILENAME:
            line = tb.tb_lineno
        tb = tb.tb_next
    return line


def _describe(exc: BaseException) -> str:
    if isinstance(exc, TemplateError):
        return exc.message or type(exc).__name__
    return f"{type(exc).__name__}: {exc}"


# --- Legend ------------------------------------------------------------------------


def _unwrap(annotation: Any) -> tuple[Any, bool]:
    """(inner type, is a list) of an annotation - `Optional` and `Annotated` removed."""
    is_list = False
    while True:
        origin = typing.get_origin(annotation)
        args = typing.get_args(annotation)
        if origin is typing.Annotated:
            annotation = args[0]
        elif origin in (typing.Union, types.UnionType):
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) != 1:
                return str, is_list
            annotation = non_none[0]
        elif origin in (list, set, tuple, frozenset, typing.Sequence):
            is_list = True
            annotation = args[0] if args else Any
        else:
            return annotation, is_list


def _scalar_type_name(tp: Any) -> str:
    if tp is bool:
        return "boolean"
    if isinstance(tp, type):
        if issubclass(tp, (int, float, Decimal)):
            return "number"
        if issubclass(tp, (datetime, date)):
            return "date"
        if issubclass(tp, (str, Enum)):
            return "text"
        if issubclass(tp, dict):
            return "object"
    return "text"


def walk_model(
    prefix: str, model: type[BaseModel], stack: tuple[type, ...] = ()
) -> list[LegendEntrySchema]:
    """Flat list of every (nested) field of a schema, as the dotted template path."""
    entries: list[LegendEntrySchema] = []
    for name, info in model.model_fields.items():
        path = f"{prefix}.{name}"
        inner, is_list = _unwrap(info.annotation)
        nested = (
            inner if isinstance(inner, type) and issubclass(inner, BaseModel) else None
        )
        if nested is not None:
            entries.append(
                LegendEntrySchema(
                    path=path,
                    type="list" if is_list else "object",
                    description=info.description,
                )
            )
            if nested not in stack:  # self-referencing schemas (parent / children)
                entries.extend(
                    walk_model(
                        f"{path}[]" if is_list else path, nested, (*stack, model)
                    )
                )
        else:
            type_name = _scalar_type_name(inner)
            entries.append(
                LegendEntrySchema(
                    path=path,
                    type=f"list of {type_name}" if is_list else type_name,
                    description=info.description,
                )
            )
    return entries


# --- Targets -----------------------------------------------------------------------


@dataclass(frozen=True)
class DocumentTargetSpec:
    target: DocumentTarget
    # the context variable(s) available in the template, e.g. `order`
    legend: Callable[[], list[LegendEntrySchema]]
    list_records: Callable[[str | None], list[DocumentRecordSchema]]
    build_context: Callable[[str], dict[str, Any]]
    default_file: str = field(default="")

    def __post_init__(self) -> None:
        if not self.default_file:
            object.__setattr__(self, "default_file", f"{self.target.value}.html.j2")


def _record(code: str, *parts: Any) -> DocumentRecordSchema:
    label = " · ".join(str(p) for p in (code, *parts) if p)
    return DocumentRecordSchema(code=code, label=label)


def _customer_name(order: Any) -> str | None:
    customer = getattr(order, "customer", None)
    return customer.name if customer else None


def _list_invoices(q: str | None) -> list[DocumentRecordSchema]:
    qs = invoice_service.get_outbound_invoices()
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(customer__name__icontains=q))
    return [_record(i.code, _customer_name(i)) for i in qs[:MAX_RECORDS]]


def _list_delivery_notes(q: str | None) -> list[DocumentRecordSchema]:
    qs = outbound_orders_service.get_outbound_orders(search_term=q, include_all=True)
    return [_record(o.code, _customer_name(o)) for o in qs[:MAX_RECORDS]]


def _list_offers(q: str | None) -> list[DocumentRecordSchema]:
    qs = outbound_calculations_service.get_calculations(search_term=q, include_all=True)
    return [_record(o.code, _customer_name(o)) for o in qs[:MAX_RECORDS]]


def _list_issue_notes(q: str | None) -> list[DocumentRecordSchema]:
    qs = warehouse_service.list_outbound_warehouse_orders(
        search_term=q, include_all=True
    )
    return [_record(o.code, _customer_name(o.order)) for o in qs[:MAX_RECORDS]]


def _list_goods_receipts(q: str | None) -> list[DocumentRecordSchema]:
    qs = warehouse_service.list_inbound_warehouse_orders(
        search_term=q, include_all=True
    )
    return [_record(o.code, _customer_name(o.order)) for o in qs[:MAX_RECORDS]]


def _invoice_legend() -> list[LegendEntrySchema]:
    section_order = InvoiceDetailSchema.model_fields["outbound_orders"].annotation
    section_model, _ = _unwrap(section_order)
    return [
        LegendEntrySchema(path="invoice", type="object"),
        *walk_model("invoice", InvoiceDetailSchema),
        LegendEntrySchema(
            path="order_sections",
            type="list",
            description="One section per invoiced order (returned goods subtracted)",
        ),
        LegendEntrySchema(path="order_sections[].order", type="object"),
        *walk_model("order_sections[].order", section_model),
        LegendEntrySchema(
            path="order_sections[].total_amount",
            type="number",
            description="Total of the order, returned goods subtracted",
        ),
        LegendEntrySchema(
            path="total_amount",
            type="number",
            description="Total of the whole invoice, returned goods subtracted",
        ),
    ]


def _root_legend(
    name: str, schema: type[BaseModel]
) -> Callable[[], list[LegendEntrySchema]]:
    return lambda: [
        LegendEntrySchema(path=name, type="object"),
        *walk_model(name, schema),
    ]


TARGETS: dict[DocumentTarget, DocumentTargetSpec] = {
    DocumentTarget.GOODS_RECEIPT: DocumentTargetSpec(
        target=DocumentTarget.GOODS_RECEIPT,
        legend=_root_legend("receipt", InboundWarehouseOrderSchema),
        list_records=_list_goods_receipts,
        build_context=lambda code: {
            "receipt": warehouse_service.get_inbound_warehouse_order(code).model_dump()
        },
    ),
    DocumentTarget.ISSUE_NOTE: DocumentTargetSpec(
        target=DocumentTarget.ISSUE_NOTE,
        legend=_root_legend("issue_note", OutboundWarehouseOrderSchema),
        list_records=_list_issue_notes,
        build_context=lambda code: {
            "issue_note": warehouse_service.get_outbound_warehouse_order(
                code
            ).model_dump()
        },
    ),
    DocumentTarget.DELIVERY_NOTE: DocumentTargetSpec(
        target=DocumentTarget.DELIVERY_NOTE,
        legend=_root_legend("order", OutboundOrderSchema),
        list_records=_list_delivery_notes,
        build_context=lambda code: {
            "order": outbound_orders_service.get_outbound_order(code).model_dump()
        },
    ),
    DocumentTarget.OUTBOUND_INVOICE: DocumentTargetSpec(
        target=DocumentTarget.OUTBOUND_INVOICE,
        legend=_invoice_legend,
        list_records=_list_invoices,
        build_context=invoice_service.get_document_context,
    ),
    DocumentTarget.OFFER: DocumentTargetSpec(
        target=DocumentTarget.OFFER,
        legend=_root_legend("offer", OutboundCalculationSchema),
        list_records=_list_offers,
        build_context=lambda code: {
            "offer": outbound_calculations_service.get_calculation(code).model_dump()
        },
    ),
}


# --- Service -----------------------------------------------------------------------


class DocumentTemplateService:
    # -- storage

    @staticmethod
    def _spec(target: DocumentTarget) -> DocumentTargetSpec:
        try:
            return TARGETS[DocumentTarget(target)]
        except (KeyError, ValueError) as e:
            raise NotFoundException(f"Unknown document target '{target}'") from e

    @classmethod
    def get_default_content(cls, target: DocumentTarget) -> str:
        spec = cls._spec(target)
        return (DEFAULT_TEMPLATES_DIR / spec.default_file).read_text(encoding="utf-8")

    @classmethod
    def get_content(cls, target: DocumentTarget) -> tuple[str, bool]:
        """(template source, is the built-in default)"""
        cls._spec(target)
        saved = DocumentTemplate.objects.filter(target=target).first()
        if saved is None:
            return cls.get_default_content(target), True
        return saved.content, False

    @classmethod
    def list_targets(cls) -> list[DocumentTargetSchema]:
        customised = set(DocumentTemplate.objects.values_list("target", flat=True))
        return [
            DocumentTargetSchema(
                target=target,
                label=DocumentTarget(target).label,
                is_default=target.value not in customised,
            )
            for target in TARGETS
        ]

    @classmethod
    def get_template(cls, target: DocumentTarget) -> DocumentTemplateSchema:
        content, is_default = cls.get_content(target)
        return DocumentTemplateSchema(
            target=target,
            label=DocumentTarget(target).label,
            content=content,
            is_default=is_default,
            legend=cls.get_legend(target),
        )

    @classmethod
    def save_template(
        cls, target: DocumentTarget, content: str
    ) -> DocumentTemplateSchema:
        cls._spec(target)
        if not content.strip():
            raise TemplateRenderError("Template must not be empty")
        cls.validate(content)
        DocumentTemplate.objects.update_or_create(
            target=target, defaults={"content": content}
        )
        return cls.get_template(target)

    @classmethod
    def reset_template(cls, target: DocumentTarget) -> DocumentTemplateSchema:
        cls._spec(target)
        DocumentTemplate.objects.filter(target=target).delete()
        return cls.get_template(target)

    # -- legend & records

    @classmethod
    def get_legend(cls, target: DocumentTarget) -> DocumentLegendSchema:
        filters = [
            LegendFilterSchema(
                name=f.name, signature=f.signature, description=f.description
            )
            for f in CUSTOM_FILTERS
        ] + [
            LegendFilterSchema(name=n, signature=sig, description=desc)
            for n, sig, desc in BUILTIN_FILTER_HELP
        ]
        return DocumentLegendSchema(fields=cls._spec(target).legend(), filters=filters)

    @classmethod
    def list_records(
        cls, target: DocumentTarget, q: str | None = None
    ) -> list[DocumentRecordSchema]:
        return cls._spec(target).list_records(q)

    # -- rendering

    @staticmethod
    def validate(content: str) -> None:
        """Raises `TemplateRenderError` if the source does not compile."""
        try:
            _environment.from_string(content)
        except JinjaSyntaxError as e:
            raise TemplateRenderError(_describe(e), e.lineno) from e
        except TemplateError as e:
            raise TemplateRenderError(_describe(e), _error_line(e)) from e

    @classmethod
    def render_html(cls, content: str, context: dict[str, Any]) -> str:
        """Generic: renders any template source over any context (sandboxed)."""
        try:
            return _environment.from_string(content).render(context)
        except JinjaSyntaxError as e:
            raise TemplateRenderError(_describe(e), e.lineno) from e
        except Exception as e:  # noqa: BLE001 - user code can fail in any way
            raise TemplateRenderError(_describe(e), _error_line(e)) from e

    @classmethod
    def render_pdf(cls, content: str, context: dict[str, Any]) -> bytes:
        return print_html_to_pdf(content_html=cls.render_html(content, context))

    @classmethod
    def _content_or_saved(cls, target: DocumentTarget, content: str | None) -> str:
        return content if content is not None else cls.get_content(target)[0]

    @classmethod
    def render_record_html(
        cls, target: DocumentTarget, record_code: str, content: str | None = None
    ) -> str:
        spec = cls._spec(target)
        return cls.render_html(
            cls._content_or_saved(target, content), spec.build_context(record_code)
        )

    @classmethod
    def render_record_pdf(
        cls, target: DocumentTarget, record_code: str, content: str | None = None
    ) -> bytes:
        return print_html_to_pdf(
            content_html=cls.render_record_html(target, record_code, content)
        )


document_template_service = DocumentTemplateService()
