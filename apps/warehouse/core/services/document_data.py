"""What each printable document offers to the layout: attributes (catalog) and values.

Every document kind is normalised into the same shape - header attributes, two parties,
item rows and summaries - so one base template can print all of them. The catalog lists
which attributes the admin may pick for each block.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

from django.db.models import Q
from django.forms.models import model_to_dict

from apps.warehouse.core.schemas.document_templates import DocumentRecordSchema
from apps.warehouse.core.services.invoices import invoice_service
from apps.warehouse.core.services.outbound_calculations import (
    outbound_calculations_service,
)
from apps.warehouse.core.services.outbound_orders import outbound_orders_service
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.customer import ContactPerson, Customer
from apps.warehouse.models.document_template import DocumentTarget

MAX_RECORDS = 50
RETURNED_SUFFIX = " (vratka)"


class Kind(StrEnum):
    TEXT = "text"
    DATE = "date"
    DATETIME = "datetime"
    QUANTITY = "quantity"  # up to 4 decimals
    MONEY = "money"  # 2 decimals + the currency of the document


@dataclass(frozen=True)
class FieldDef:
    key: str
    label: str  # default caption
    kind: Kind = Kind.TEXT


@dataclass
class DocumentData:
    code: str
    currency: str | None
    header: dict[str, Any]
    customer: dict[str, Any] | None
    supplier: dict[str, Any] | None
    items: list[dict[str, Any]]
    summaries: dict[str, Any]


F = FieldDef
PARTY_FIELDS = [
    F("name", "Název"),
    F("address", "Adresa"),
    F("street", "Ulice"),
    F("city", "Město"),
    F("postal_code", "PSČ"),
    F("country", "Země"),
    F("identification", "IČO"),
    F("tax_identification", "DIČ"),
    F("email", "E-mail"),
    F("phone", "Telefon"),
    F("code", "Kód"),
]

# the selected contact person of the document (orders, offers, ...)
CONTACT_FIELDS = [
    F("contact_name", "Kontakt - jméno"),
    F("contact_email", "Kontakt - e-mail"),
    F("contact_phone", "Kontakt - telefon"),
    F("contact_address", "Kontakt - adresa"),
    F("contact_street", "Kontakt - ulice"),
    F("contact_city", "Kontakt - město"),
    F("contact_postal_code", "Kontakt - PSČ"),
    F("contact_country", "Kontakt - země"),
    F("contact_note", "Kontakt - poznámka"),
]
DOCUMENT_CODE = F("code", "Kód dokladu")
# evaluated when the document is printed (not stored)
PRINTED_AT = F("printed_at", "Vytištěno", Kind.DATETIME)

ITEM_INDEX = F("index", "#")
PRODUCT_CODE = F("product_code", "Kód")
PRODUCT_NAME = F("product_name", "Název")
AMOUNT = F("amount", "Množství", Kind.QUANTITY)
UNIT = F("unit", "MJ")
UNIT_PRICE = F("unit_price", "Cena / MJ", Kind.MONEY)
TOTAL_PRICE = F("total_price", "Celkem", Kind.MONEY)
ORIGIN = F("origin_country", "Země původu")
BATCH = F("batch", "Šarže")

ITEMS_COUNT = F("items_count", "Počet položek", Kind.QUANTITY)
TOTAL_QUANTITY = F("total_quantity", "Celkové množství", Kind.QUANTITY)
TOTAL_AMOUNT = F("total_amount", "Celkem", Kind.MONEY)


@dataclass(frozen=True)
class DocumentSpec:
    target: DocumentTarget
    header_fields: list[FieldDef]
    item_columns: list[FieldDef]
    summaries: list[FieldDef]
    list_records: Callable[[str | None], list[DocumentRecordSchema]]
    build: Callable[[str], DocumentData]
    has_contact: bool = False  # the document has a contact person of the customer
    _by_block: dict[str, dict[str, FieldDef]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    @property
    def customer_fields(self) -> list[FieldDef]:
        return [
            *PARTY_FIELDS,
            *(CONTACT_FIELDS if self.has_contact else []),
            PRINTED_AT,
        ]

    def fields_of(self, block: str) -> dict[str, FieldDef]:
        """Attributes of a block by key.

        "header" | "supplier" | "customer" | "items" | "summaries"
        """
        if not self._by_block:
            self._by_block.update(
                header={
                    f.key: f for f in (DOCUMENT_CODE, PRINTED_AT, *self.header_fields)
                },
                supplier={f.key: f for f in (*PARTY_FIELDS, PRINTED_AT)},
                customer={f.key: f for f in self.customer_fields},
                items={f.key: f for f in (*self.item_columns, PRINTED_AT)},
                summaries={f.key: f for f in (*self.summaries, PRINTED_AT)},
            )
        return self._by_block[block]


# --- helpers -----------------------------------------------------------------------


def _address(street: Any, city: Any, postal_code: Any) -> str:
    locality = " ".join(p for p in (postal_code, city) if p)
    return ", ".join(p for p in (street, locality) if p)


def _contact_values(contact: dict[str, Any] | None) -> dict[str, Any]:
    if not contact:
        return {}
    return {
        "contact_name": _contact_name(contact),
        "contact_email": contact.get("email"),
        "contact_phone": contact.get("phone"),
        "contact_address": _address(
            contact.get("street"), contact.get("city"), contact.get("postal_code")
        ),
        "contact_street": contact.get("street"),
        "contact_city": contact.get("city"),
        "contact_postal_code": contact.get("postal_code"),
        "contact_country": contact.get("state"),
        "contact_note": contact.get("note"),
    }


def _party(
    code: str | None, contact: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    customer = Customer.objects.filter(code=code).first() if code else None
    if customer is None:
        return None
    return {
        **_contact_values(contact),
        "name": customer.name,
        "address": _address(customer.street, customer.city, customer.postal_code),
        "street": customer.street,
        "city": customer.city,
        "postal_code": customer.postal_code,
        "country": customer.state,
        "identification": customer.identification,
        "tax_identification": customer.tax_identification,
        "email": customer.email,
        "phone": customer.phone,
        "code": customer.code,
    }


def _order_contact(order_code: str) -> dict[str, Any] | None:
    """Contact person of an outbound order (the warehouse order only references it)."""
    contact = ContactPerson.objects.filter(outbound_orders__code=order_code).first()
    return model_to_dict(contact) if contact else None


def _contact_name(contact: dict[str, Any] | None) -> str | None:
    if not contact:
        return None
    parts = (
        contact.get("title_pre"),
        contact.get("first_name"),
        contact.get("middle_name"),
        contact.get("last_name"),
        contact.get("title_post"),
    )
    return " ".join(p for p in parts if p) or None


def _dec(value: Any) -> Decimal:
    return Decimal(str(value if value is not None else 0))


def _sum(rows: list[dict[str, Any]], key: str) -> Decimal:
    return sum((_dec(r[key]) for r in rows if r.get(key) is not None), Decimal("0"))


def _price_item(item: dict[str, Any], *, unit_price: Any, total_price: Any) -> dict:
    """Item row of a priced document; goods taken back are subtracted."""
    returned = bool(item.get("is_returned"))
    product = item["product"]
    sign = -1 if returned else 1
    return {
        "index": item["index"] + 1 if item.get("index") is not None else None,
        "product_code": product["code"],
        "product_name": product["name"] + (RETURNED_SUFFIX if returned else ""),
        "amount": item["amount"],
        "unit": product.get("unit"),
        "unit_price": unit_price,
        "total_price": _dec(total_price) * sign,
        "origin_country": item.get("required_origin_country")
        or item.get("origin_country"),
        "customer_product_code": item.get("customer_product_code"),
        "note": item.get("note"),
    }


def _priced_summaries(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "items_count": len(items),
        "total_quantity": _sum(items, "amount"),
        "total_amount": _sum(items, "total_price"),
    }


def _record(code: str, *parts: Any) -> DocumentRecordSchema:
    label = " · ".join(str(p) for p in (code, *parts) if p)
    return DocumentRecordSchema(code=code, label=label)


def _customer_name(order: Any) -> str | None:
    customer = getattr(order, "customer", None)
    return customer.name if customer else None


# --- invoice -----------------------------------------------------------------------


def _list_invoices(q: str | None) -> list[DocumentRecordSchema]:
    qs = invoice_service.get_outbound_invoices()
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(customer__name__icontains=q))
    return [_record(i.code, _customer_name(i)) for i in qs[:MAX_RECORDS]]


def _build_invoice(code: str) -> DocumentData:
    invoice = invoice_service.get_invoice(code)
    items: list[dict[str, Any]] = []
    for order in invoice_service.get_related_orders(invoice):
        for item in order.items:
            row = _price_item(
                item.model_dump(),
                unit_price=item.unit_price,
                total_price=item.total_price,
            )
            row["order_code"] = order.code
            items.append(row)
    payment = invoice.payment_method
    return DocumentData(
        code=invoice.code,
        currency=invoice.currency,
        header={
            "issued_date": invoice.issued_date,
            "due_date": invoice.due_date,
            "taxable_supply_date": invoice.taxable_supply_date,
            "paid_date": invoice.paid_date,
            "payment_method": payment.name if payment else None,
            "external_code": invoice.external_code,
            "currency": invoice.currency,
            "note": invoice.note,
        },
        customer=_party(invoice.customer.code if invoice.customer else None),
        supplier=_party(invoice.supplier.code if invoice.supplier else None),
        items=items,
        summaries=_priced_summaries(items),
    )


# --- outbound order (delivery note) / calculation (offer) --------------------------


def _list_delivery_notes(q: str | None) -> list[DocumentRecordSchema]:
    qs = outbound_orders_service.get_outbound_orders(search_term=q, include_all=True)
    return [_record(o.code, _customer_name(o)) for o in qs[:MAX_RECORDS]]


def _list_offers(q: str | None) -> list[DocumentRecordSchema]:
    qs = outbound_calculations_service.get_calculations(search_term=q, include_all=True)
    return [_record(o.code, _customer_name(o)) for o in qs[:MAX_RECORDS]]


def _build_outbound_document(doc: Any, extra_header: dict[str, Any]) -> DocumentData:
    items = [
        _price_item(
            item.model_dump(),
            unit_price=item.document_unit_price,
            total_price=item.document_total_price,
        )
        for item in sorted(doc.items, key=lambda i: i.index)
    ]
    return DocumentData(
        code=doc.code,
        currency=doc.document_currency,
        header={
            "external_code": doc.external_code,
            "state": doc.state,
            "created": doc.created,
            "requested_delivery_date": doc.requested_delivery_date,
            "currency": doc.document_currency,
            "contact": _contact_name(doc.contact.model_dump() if doc.contact else None),
            "description": doc.description,
            "note": doc.note,
            **extra_header,
        },
        customer=_party(
            doc.customer.code, doc.contact.model_dump() if doc.contact else None
        ),
        supplier=_party(doc.supplier.code),
        items=items,
        summaries=_priced_summaries(items),
    )


def _build_delivery_note(code: str) -> DocumentData:
    order = outbound_orders_service.get_outbound_order(code)
    return _build_outbound_document(order, {"fulfilled_date": order.fulfilled_date})


def _build_offer(code: str) -> DocumentData:
    return _build_outbound_document(
        outbound_calculations_service.get_calculation(code), {}
    )


# --- warehouse orders (issue note / goods receipt) ---------------------------------


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


def _stock_item(item: Any, position: int, **extra: Any) -> dict[str, Any]:
    return {
        "index": position,
        "product_code": item.product.code,
        "product_name": item.product.name,
        "amount": item.amount,
        "unit": item.unit_of_measure,
        **extra,
    }


def _warehouse_summaries(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "items_count": len(items),
        "total_quantity": _sum(items, "amount"),
        "total_amount": _sum(items, "total_price"),
    }


def _build_issue_note(code: str) -> DocumentData:
    note = warehouse_service.get_outbound_warehouse_order(code)
    items = [
        _stock_item(
            item,
            position,
            batch=item.desired_batch_code,
            origin_country=item.required_origin_country,
        )
        for position, item in enumerate(
            sorted(note.order_items, key=lambda i: i.index), 1
        )
    ]
    return DocumentData(
        code=note.code,
        currency=None,
        header={
            "order_code": note.order_code,
            "state": note.state,
            "created": note.created,
        },
        customer=_party(note.order.customer.code, _order_contact(note.order.code)),
        supplier=_party(note.order.supplier.code),
        items=items,
        summaries=_warehouse_summaries(items),
    )


def _build_goods_receipt(code: str) -> DocumentData:
    receipt = warehouse_service.get_inbound_warehouse_order(code)
    items = [
        _stock_item(
            item,
            position,
            unit_price=item.unit_price_at_receipt,
            total_price=item.unit_price_at_receipt * item.amount,
            batch=item.batch_barcode,
            origin_country=item.origin_country,
        )
        for position, item in enumerate(
            sorted(receipt.order_items, key=lambda i: i.index), 1
        )
    ]
    return DocumentData(
        code=receipt.code,
        currency=receipt.currency,
        header={
            "order_code": receipt.order_code,
            "state": receipt.state,
            "created": receipt.created,
            "currency": receipt.currency,
        },
        customer=_party(receipt.order.customer.code),
        supplier=_party(receipt.order.supplier.code),
        items=items,
        summaries=_warehouse_summaries(items),
    )


# --- catalog -----------------------------------------------------------------------

_PRICED_ITEMS = [
    ITEM_INDEX,
    PRODUCT_CODE,
    PRODUCT_NAME,
    F("customer_product_code", "Kód zákazníka"),
    AMOUNT,
    UNIT,
    UNIT_PRICE,
    TOTAL_PRICE,
    ORIGIN,
    F("note", "Poznámka"),
]
_PRICED_SUMMARIES = [TOTAL_AMOUNT, ITEMS_COUNT, TOTAL_QUANTITY]
_OUTBOUND_HEADER = [
    F("external_code", "Externí kód"),
    F("state", "Stav"),
    F("created", "Vytvořeno", Kind.DATETIME),
    F("requested_delivery_date", "Požadované dodání", Kind.DATETIME),
    F("currency", "Měna"),
    F("contact", "Kontaktní osoba"),
    F("description", "Popis"),
    F("note", "Poznámka"),
]

SPECS: dict[DocumentTarget, DocumentSpec] = {
    DocumentTarget.OUTBOUND_INVOICE: DocumentSpec(
        target=DocumentTarget.OUTBOUND_INVOICE,
        header_fields=[
            F("issued_date", "Vystaveno", Kind.DATE),
            F("due_date", "Splatnost", Kind.DATE),
            F("taxable_supply_date", "DUZP", Kind.DATE),
            F("paid_date", "Uhrazeno", Kind.DATE),
            F("payment_method", "Způsob platby"),
            F("external_code", "Externí číslo"),
            F("currency", "Měna"),
            F("note", "Poznámka"),
        ],
        item_columns=[
            *_PRICED_ITEMS[:3],
            F("order_code", "Objednávka"),
            *_PRICED_ITEMS[3:],
        ],
        summaries=_PRICED_SUMMARIES,
        list_records=_list_invoices,
        build=_build_invoice,
    ),
    DocumentTarget.DELIVERY_NOTE: DocumentSpec(
        target=DocumentTarget.DELIVERY_NOTE,
        header_fields=[
            *_OUTBOUND_HEADER,
            F("fulfilled_date", "Vyřízeno", Kind.DATETIME),
        ],
        item_columns=_PRICED_ITEMS,
        summaries=_PRICED_SUMMARIES,
        list_records=_list_delivery_notes,
        build=_build_delivery_note,
        has_contact=True,
    ),
    DocumentTarget.OFFER: DocumentSpec(
        target=DocumentTarget.OFFER,
        header_fields=_OUTBOUND_HEADER,
        item_columns=_PRICED_ITEMS,
        summaries=_PRICED_SUMMARIES,
        list_records=_list_offers,
        build=_build_offer,
        has_contact=True,
    ),
    DocumentTarget.ISSUE_NOTE: DocumentSpec(
        target=DocumentTarget.ISSUE_NOTE,
        header_fields=[
            F("order_code", "Objednávka"),
            F("state", "Stav"),
            F("created", "Vytvořeno", Kind.DATETIME),
        ],
        item_columns=[
            ITEM_INDEX,
            PRODUCT_CODE,
            PRODUCT_NAME,
            AMOUNT,
            UNIT,
            BATCH,
            ORIGIN,
        ],
        summaries=[ITEMS_COUNT, TOTAL_QUANTITY],
        list_records=_list_issue_notes,
        build=_build_issue_note,
        has_contact=True,
    ),
    DocumentTarget.GOODS_RECEIPT: DocumentSpec(
        target=DocumentTarget.GOODS_RECEIPT,
        header_fields=[
            F("order_code", "Objednávka"),
            F("state", "Stav"),
            F("created", "Vytvořeno", Kind.DATETIME),
            F("currency", "Měna"),
        ],
        item_columns=[
            ITEM_INDEX,
            PRODUCT_CODE,
            PRODUCT_NAME,
            AMOUNT,
            UNIT,
            UNIT_PRICE,
            TOTAL_PRICE,
            BATCH,
            ORIGIN,
        ],
        summaries=[TOTAL_AMOUNT, ITEMS_COUNT, TOTAL_QUANTITY],
        list_records=_list_goods_receipts,
        build=_build_goods_receipt,
    ),
}
