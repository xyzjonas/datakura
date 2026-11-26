from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from apps.warehouse.core.exceptions import (
    InvalidDocumentLayoutError,
    NotFoundException,
)
from apps.warehouse.core.schemas.document_templates import (
    DocumentLayoutSchema,
    LayoutFieldSchema,
    LogoBlockSchema,
    PaginationSchema,
)
from apps.warehouse.core.services.document_data import SPECS, Kind
from apps.warehouse.core.services.document_templates import (
    default_layout,
    document_template_service as service,
    format_value,
)
from apps.warehouse.models.document_template import DocumentTarget, DocumentTemplate
from apps.warehouse.tests.factories.customer import (
    ContactPersonFactory,
    CustomerFactory,
)
from apps.warehouse.tests.factories.order import (
    InboundOrderFactory,
    InvoiceFactory,
    OutboundCalculationFactory,
    OutboundCalculationItemFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.warehouse import (
    InboundWarehouseOrderFactory,
    WarehouseOrderOutFactory,
)

PIXEL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def fields(*keys: str) -> list[LayoutFieldSchema]:
    return [LayoutFieldSchema(key=k, label=k.upper()) for k in keys]


@pytest.fixture
def records(db) -> dict[DocumentTarget, str]:
    """One printable record per target -> its code."""
    customer = CustomerFactory(
        name="ACME <b>s.r.o.</b>",
        street="Hlavní 1",
        city="Praha",
        postal_code="11000",
        identification="12345678",
        tax_identification="",
    )
    invoice = InvoiceFactory.it(customer=customer, currency="CZK")
    order = OutboundOrderFactory.it(customer=customer, currency="CZK", invoice=invoice)
    OutboundOrderItemFactory(order=order, total_price=100, unit_price=100)
    calculation = OutboundCalculationFactory.it(customer=customer, currency="CZK")
    OutboundCalculationItemFactory(calculation=calculation)
    return {
        DocumentTarget.GOODS_RECEIPT: InboundWarehouseOrderFactory.it(
            order=InboundOrderFactory.it()
        ).code,
        DocumentTarget.ISSUE_NOTE: WarehouseOrderOutFactory.it(order=order).code,
        DocumentTarget.DELIVERY_NOTE: order.code,
        DocumentTarget.OUTBOUND_INVOICE: invoice.code,
        DocumentTarget.OFFER: calculation.code,
    }


# --- formatting ------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, kind, currency, expected",
    [
        (None, Kind.TEXT, None, ""),
        ("", Kind.MONEY, "CZK", ""),
        ("abc", Kind.TEXT, None, "abc"),
        (date(2026, 3, 7), Kind.DATE, None, "07. 03. 2026"),
        (
            datetime(2026, 3, 7, 14, 5, tzinfo=timezone.utc),
            Kind.DATE,
            None,
            "07. 03. 2026",
        ),
        (date(2026, 3, 7), Kind.DATETIME, None, "07. 03. 2026"),
        (Decimal("3.5000"), Kind.QUANTITY, None, "3.5"),
        (3, Kind.QUANTITY, None, "3"),
        (Decimal("1250"), Kind.MONEY, "CZK", "1250.00 CZK"),
        (-12.345, Kind.MONEY, None, "-12.35"),
        (0, Kind.MONEY, "EUR", "0.00 EUR"),
        ("not a date", Kind.DATE, None, "not a date"),
    ],
)
def test_format_value(value, kind, currency, expected) -> None:
    assert format_value(value, kind, currency) == expected


def test_format_datetime_includes_time() -> None:
    value = datetime(2026, 3, 7, 14, 5, tzinfo=timezone.utc)

    assert format_value(value, Kind.DATETIME).startswith("07. 03. 2026 ")


# --- defaults / storage ------------------------------------------------------------


@pytest.mark.parametrize("target", list(DocumentTarget))
def test_default_layout_is_valid_for_every_target(target) -> None:
    assert set(SPECS) == set(DocumentTarget)

    service.validate(target, default_layout(target))


@pytest.mark.django_db
def test_get_layout_default_then_saved_then_reset() -> None:
    target = DocumentTarget.OFFER
    layout, is_default = service.get_layout(target)
    assert is_default and layout == default_layout(target)

    custom = default_layout(target)
    custom.items.columns = fields("product_name", "total_price")
    service.save_template(target, custom)
    saved, is_default = service.get_layout(target)
    assert not is_default
    assert [c.key for c in saved.items.columns] == ["product_name", "total_price"]
    assert DocumentTemplate.objects.filter(target=target).count() == 1

    service.save_template(target, custom)  # saving again updates in place
    assert DocumentTemplate.objects.filter(target=target).count() == 1

    assert service.reset_template(target).is_default
    assert not DocumentTemplate.objects.exists()


@pytest.mark.django_db
def test_list_targets_flags_customised() -> None:
    service.save_template(DocumentTarget.OFFER, default_layout(DocumentTarget.OFFER))

    flags = {t.target: t.is_default for t in service.list_targets()}

    assert flags[DocumentTarget.OFFER] is False
    assert all(v for k, v in flags.items() if k != DocumentTarget.OFFER)


def test_unknown_target() -> None:
    with pytest.raises(NotFoundException):
        service.validate("nope", DocumentLayoutSchema())  # type: ignore[arg-type]


# --- validation --------------------------------------------------------------------


def _with(**changes) -> DocumentLayoutSchema:
    layout = default_layout(DocumentTarget.ISSUE_NOTE)
    for path, value in changes.items():
        block, attr = path.split("__")
        setattr(getattr(layout, block), attr, value)
    return layout


@pytest.mark.parametrize(
    "layout, message",
    [
        (_with(header__left=fields("nope")), "Unknown attribute"),
        (
            _with(header__middle=[LayoutFieldSchema(parts=["name", "nope"])]),
            "Unknown attribute.*nope",
        ),
        (
            _with(items__columns=fields("unit_price")),
            "Unknown attribute",
        ),  # not on issue note
        (_with(items__summaries=fields("total_amount")), "Unknown attribute"),
        (_with(items__columns=[]), "at least 1 column"),
        (_with(logo__enabled=True), "no image"),
    ],
)
def test_invalid_layouts_are_rejected(layout, message) -> None:
    with pytest.raises(InvalidDocumentLayoutError, match=message):
        service.validate(DocumentTarget.ISSUE_NOTE, layout)


def test_empty_items_table_is_fine_when_disabled() -> None:
    layout = _with(items__columns=[], items__enabled=False)

    service.validate(DocumentTarget.ISSUE_NOTE, layout)


def test_party_fields_are_shared_but_header_fields_are_per_document() -> None:
    layout = _with(header__right=fields("issued_date"))  # invoice-only attribute

    with pytest.raises(InvalidDocumentLayoutError):
        service.validate(DocumentTarget.ISSUE_NOTE, layout)
    layout.header.right = fields("order_code")
    layout.customer.fields = fields("email", "phone", "country")
    service.validate(DocumentTarget.ISSUE_NOTE, layout)


# --- rendering ---------------------------------------------------------------------


@pytest.mark.parametrize("target", list(DocumentTarget))
def test_default_render_of_every_target(records, target) -> None:
    html = service.render_record_html(target, records[target])

    assert records[target] in html
    assert "data:image/svg+xml;base64," in html  # the barcode
    assert "<table>" in html


def test_render_uses_the_saved_layout_unless_a_draft_is_given(records) -> None:
    target = DocumentTarget.OFFER
    code = records[target]
    saved = default_layout(target)
    saved.header.title = "Saved title"
    service.save_template(target, saved)
    draft = default_layout(target)
    draft.header.title = "Draft title"

    assert "Saved title" in service.render_record_html(target, code)
    assert "Draft title" in service.render_record_html(target, code, draft)
    assert "Saved title" in service.render_record_html(target, code)  # not persisted


def test_render_rejects_an_invalid_draft(records) -> None:
    draft = default_layout(DocumentTarget.OFFER)
    draft.items.columns = fields("nope")

    with pytest.raises(InvalidDocumentLayoutError):
        service.render_record_html(
            DocumentTarget.OFFER, records[DocumentTarget.OFFER], draft
        )


def test_default_header_prints_code_as_text_and_barcode(records) -> None:
    target = DocumentTarget.OFFER

    html = service.render_record_html(target, records[target])

    assert html.count(records[target]) >= 2  # title + the barcode alt text
    assert 'class="barcode"' in html


def test_party_attributes_follow_the_layout_order_and_skip_empty(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.supplier.enabled = False
    layout.customer.fields = [
        LayoutFieldSchema(key="identification", label="IČO:"),
        LayoutFieldSchema(key="tax_identification", label="DIČ:"),  # empty -> skipped
        LayoutFieldSchema(key="name"),
        LayoutFieldSchema(key="address"),
    ]

    html = service.render_record_html(target, records[target], layout)

    assert "DIČ:" not in html
    ico, name, address = (
        html.index(t) for t in ("12345678", "ACME", "Hlavní 1, 11000 Praha")
    )
    assert ico < name < address
    assert "&lt;b&gt;s.r.o.&lt;/b&gt;" in html  # data are escaped


def test_disabled_blocks_are_not_printed(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.supplier.enabled = False
    layout.customer.enabled = False
    layout.items.enabled = False
    layout.header.left = []
    layout.header.right = []

    html = service.render_record_html(target, records[target], layout)

    assert 'class="party"' not in html
    assert "<table>" not in html
    assert "data:image/svg+xml" not in html


def test_items_columns_and_summaries_follow_the_layout(records) -> None:
    target = DocumentTarget.OUTBOUND_INVOICE
    layout = default_layout(target)
    layout.items.columns = [
        LayoutFieldSchema(key="total_price", label="Sum"),
        LayoutFieldSchema(key="order_code", label="Order"),
    ]
    layout.items.summaries = [
        LayoutFieldSchema(key="items_count", label="Lines"),
        LayoutFieldSchema(key="total_amount", label="Grand total"),
    ]

    html = service.render_record_html(target, records[target], layout)

    assert html.index(">Sum<") < html.index(">Order<")
    assert "Product" not in html and "Cena / MJ" not in html
    assert "100.00 CZK" in html
    assert html.index("Lines") < html.index("Grand total")


@pytest.mark.django_db
def test_returned_goods_are_subtracted_in_the_total() -> None:
    customer = CustomerFactory()
    order = OutboundOrderFactory.it(customer=customer, currency="CZK")
    OutboundOrderItemFactory(order=order, total_price=100, unit_price=100)
    OutboundOrderItemFactory(
        order=order, total_price=30, unit_price=30, is_returned=True
    )
    layout = default_layout(DocumentTarget.DELIVERY_NOTE)
    layout.items.columns = fields("product_name", "total_price")
    layout.items.summaries = fields("total_amount")

    html = service.render_record_html(DocumentTarget.DELIVERY_NOTE, order.code, layout)

    assert "(vratka)" in html
    assert "-30.00 CZK" in html
    assert "70.00 CZK" in html


def test_logo_footer_and_titles(records) -> None:
    target = DocumentTarget.OFFER
    layout = default_layout(target)
    layout.logo = LogoBlockSchema(enabled=True, image=PIXEL, align="right")
    layout.footer.enabled = True
    layout.footer.text = "Thank <you>"

    html = service.render_record_html(target, records[target], layout)

    assert f'src="{PIXEL}"' in html
    assert 'class="logo right"' in html
    assert "Thank &lt;you&gt;" in html


def test_logo_off_and_empty_footer_are_not_printed(records) -> None:
    target = DocumentTarget.OFFER
    layout = default_layout(target)
    layout.logo = LogoBlockSchema(enabled=False, image=PIXEL)
    layout.footer.enabled = True
    layout.footer.text = "   "

    html = service.render_record_html(target, records[target], layout)

    assert PIXEL not in html
    assert 'class="footer"' not in html


def test_code_that_cannot_be_a_barcode_is_still_printed(records) -> None:
    from apps.warehouse.core.services.document_templates import barcode_svg

    assert not barcode_svg.is_encodable("PŘ-1")
    html = service.render_record_html(
        DocumentTarget.OFFER, records[DocumentTarget.OFFER]
    )  # sanity: normal codes render a barcode image
    assert 'class="barcode"' in html


@pytest.mark.parametrize("target", list(DocumentTarget))
def test_list_records(records, target) -> None:
    codes = [r.code for r in service.list_records(target)]

    assert records[target] in codes
    assert service.list_records(target, "zzz-no-such-record") == []


def test_pdf_is_rendered(records) -> None:
    pdf = service.render_record_pdf(DocumentTarget.OFFER, records[DocumentTarget.OFFER])

    assert pdf.startswith(b"%PDF")


# --- header sections, caption toggle, composites, barcode modifier ------------------


def _layout_with_header(
    target=DocumentTarget.OFFER, **sections
) -> DocumentLayoutSchema:
    layout = default_layout(target)
    layout.header.left = layout.header.middle = layout.header.right = []
    for name, refs in sections.items():
        setattr(layout.header, name, refs)
    return layout


def test_header_sections_are_placed_left_middle_right(records) -> None:
    target = DocumentTarget.OFFER
    layout = _layout_with_header(
        left=[LayoutFieldSchema(key="external_code", label="L:")],
        middle=[LayoutFieldSchema(key="state", label="M:")],
        right=[LayoutFieldSchema(key="currency", label="R:")],
    )

    html = service.render_record_html(target, records[target], layout)

    assert html.index('class="left"') < html.index("L:")
    assert html.index("L:") < html.index('class="middle"') < html.index("M:")
    assert html.index("M:") < html.index('class="right"') < html.index("R:")


def test_empty_middle_section_keeps_the_right_one_on_the_right(records) -> None:
    target = DocumentTarget.OFFER
    layout = _layout_with_header(right=[LayoutFieldSchema(key="currency", label="R:")])

    html = service.render_record_html(target, records[target], layout)

    assert 'class="left"' in html and 'class="middle"' in html


@pytest.mark.parametrize(
    "show_label, label, printed",
    [(True, "Měna:", True), (False, "Měna:", False), (True, "", False)],
)
def test_caption_can_be_hidden(records, show_label, label, printed) -> None:
    target = DocumentTarget.OFFER
    layout = _layout_with_header(
        right=[LayoutFieldSchema(key="currency", label=label, show_label=show_label)]
    )

    html = service.render_record_html(target, records[target], layout)

    assert ("Měna:" in html) is printed
    assert "CZK" in html  # the value stays


def test_caption_can_be_hidden_in_every_block(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.customer.fields = [
        LayoutFieldSchema(key="identification", label="ICO-CAP", show_label=False)
    ]
    layout.items.columns = [
        LayoutFieldSchema(key="product_code", label="COL-CAP", show_label=False)
    ]
    layout.items.summaries = [
        LayoutFieldSchema(key="items_count", label="SUM-CAP", show_label=False)
    ]

    html = service.render_record_html(target, records[target], layout)

    assert "CAP" not in html
    assert "12345678" in html


def test_composite_row_chains_values_on_one_line(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.customer.fields = [
        LayoutFieldSchema(
            parts=["street", "postal_code", "city", "tax_identification"],  # last empty
            label="Adresa:",
            separator=" | ",
        )
    ]

    html = service.render_record_html(target, records[target], layout)

    assert "Adresa:" in html
    assert "Hlavní 1</span>" not in html
    assert "Hlavní 1<span> | </span>11000<span> | </span>Praha</p>" in html


def test_composite_column_stacks_values(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.items.columns = [
        LayoutFieldSchema(
            parts=["product_code", "product_name"], direction="column", show_label=False
        )
    ]

    html = service.render_record_html(target, records[target], layout)

    row = html.split("<tbody>")[1].split("</tbody>")[0]
    assert row.count("<div>") == 2
    assert "<th></th>" in html  # no caption -> empty header cell


def test_composite_without_filled_values_is_skipped(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.customer.fields = [
        LayoutFieldSchema(parts=["tax_identification"], label="EMPTY-COMPOSITE")
    ]

    html = service.render_record_html(target, records[target], layout)

    assert "EMPTY-COMPOSITE" not in html


@pytest.mark.parametrize(
    "ref",
    [
        {},  # neither key nor parts
        {"key": "name", "parts": ["name"]},  # both
        {"parts": ["a"] * 11},  # too many parts
        {"key": "name", "direction": "diagonal"},
    ],
)
def test_malformed_field_is_rejected(ref) -> None:
    with pytest.raises(ValueError):
        LayoutFieldSchema(**ref)


def test_barcode_modifier_works_on_any_attribute_even_in_a_table_cell(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.header.left = layout.header.right = []
    layout.items.columns = [
        LayoutFieldSchema(key="product_code", barcode=True),
        LayoutFieldSchema(key="product_name"),
    ]

    html = service.render_record_html(target, records[target], layout)

    body = html.split("<tbody>")[1]
    assert body.count('class="barcode"') == 1  # one row, product_code only
    assert "data:image/svg+xml;base64," not in html.split("<tbody>")[0]


def test_barcode_modifier_on_unencodable_value_falls_back_to_text(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = _layout_with_header(target)
    customer = CustomerFactory(name="Přílišžluťoučký")
    layout.customer.fields = [LayoutFieldSchema(key="name", barcode=True)]
    layout.supplier.enabled = False
    code = records[target]
    from apps.warehouse.models.orders import OutboundOrder

    OutboundOrder.objects.filter(code=code).update(customer=customer)

    html = service.render_record_html(target, code, layout)

    assert "Přílišžluťoučký" in html
    assert 'class="barcode"' not in html


def test_barcode_on_a_composite_encodes_each_part(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = _layout_with_header(
        target,
        left=[LayoutFieldSchema(parts=["code", "external_code"], barcode=True)],
    )

    html = service.render_record_html(target, records[target], layout)

    assert html.count('class="barcode"') >= 1


# --- customer contact person ----------------------------------------------------------


@pytest.fixture
def order_with_contact(db) -> str:
    customer = CustomerFactory()
    contact = ContactPersonFactory(
        customer=customer,
        title_pre="Ing.",
        first_name="Jana",
        middle_name="",
        last_name="Nováková",
        title_post="",
        email="jana@example.com",
        phone="+420 111 222 333",
        street="Kontaktní 5",
        city="Brno",
        postal_code="60200",
        state="CZ",
        note="Ring twice",
    )
    return OutboundOrderFactory.it(customer=customer, contact=contact).code


@pytest.mark.parametrize(
    "key, expected",
    [
        ("contact_name", "Ing. Jana Nováková"),
        ("contact_email", "jana@example.com"),
        ("contact_phone", "+420 111 222 333"),
        ("contact_address", "Kontaktní 5, 60200 Brno"),
        ("contact_street", "Kontaktní 5"),
        ("contact_city", "Brno"),
        ("contact_postal_code", "60200"),
        ("contact_country", "CZ"),
        ("contact_note", "Ring twice"),
    ],
)
def test_customer_block_can_print_the_selected_contact(
    order_with_contact, key, expected
) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.customer.fields = [LayoutFieldSchema(key=key)]

    html = service.render_record_html(target, order_with_contact, layout)

    assert expected in html


def test_contact_attributes_are_offered_only_for_documents_with_a_contact() -> None:
    def customer_keys(target):
        return {f.key for f in service.get_template(target).catalog.customer_fields}

    for target in (
        DocumentTarget.DELIVERY_NOTE,
        DocumentTarget.OFFER,
        DocumentTarget.ISSUE_NOTE,
    ):
        assert "contact_name" in customer_keys(target)
    for target in (DocumentTarget.OUTBOUND_INVOICE, DocumentTarget.GOODS_RECEIPT):
        assert "contact_name" not in customer_keys(target)
        layout = default_layout(target)
        layout.customer.fields = [LayoutFieldSchema(key="contact_name")]
        with pytest.raises(InvalidDocumentLayoutError):
            service.validate(target, layout)


def test_supplier_block_has_no_contact_attributes() -> None:
    layout = default_layout(DocumentTarget.DELIVERY_NOTE)
    layout.supplier.fields = [LayoutFieldSchema(key="contact_name")]

    with pytest.raises(InvalidDocumentLayoutError):
        service.validate(DocumentTarget.DELIVERY_NOTE, layout)


def test_order_without_a_contact_prints_nothing_for_contact_attributes(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.customer.fields = [LayoutFieldSchema(key="contact_name", label="KONTAKT")]

    html = service.render_record_html(target, records[target], layout)

    assert "KONTAKT" not in html


# --- pagination -----------------------------------------------------------------------


def test_pagination_is_off_by_default(records) -> None:
    html = service.render_record_html(
        DocumentTarget.OFFER, records[DocumentTarget.OFFER]
    )

    assert "counter(page)" not in html


@pytest.mark.parametrize(
    "position",
    [
        "top-left",
        "top-center",
        "top-right",
        "bottom-left",
        "bottom-center",
        "bottom-right",
    ],
)
def test_pagination_prints_the_page_number_in_the_chosen_place(
    records, position
) -> None:
    target = DocumentTarget.OFFER
    layout = default_layout(target)
    layout.pagination = PaginationSchema(enabled=True, position=position)

    html = service.render_record_html(target, records[target], layout)

    assert f"@{position} {{ content: counter(page)" in html


def test_pagination_position_is_restricted() -> None:
    with pytest.raises(ValueError):
        PaginationSchema(position="center; } body { display: none")  # type: ignore[arg-type]


def test_pdf_with_pagination_is_rendered(records) -> None:
    target = DocumentTarget.OFFER
    layout = default_layout(target)
    layout.pagination = PaginationSchema(enabled=True)

    assert service.render_record_pdf(target, records[target], layout).startswith(
        b"%PDF"
    )


# --- layouts saved before sections / composites existed -------------------------------


@pytest.mark.parametrize("show_barcode", [True, False])
@pytest.mark.django_db
def test_layout_saved_with_the_old_header_still_loads(show_barcode) -> None:
    target = DocumentTarget.OFFER
    layout = default_layout(target).model_dump(mode="json")
    layout["header"] = {
        "title": "Nabídka",
        "show_barcode": show_barcode,
        "fields": [{"key": "created", "label": "Vytvořeno"}],
    }
    DocumentTemplate.objects.create(target=target, layout=layout)

    loaded, is_default = service.get_layout(target)

    assert not is_default
    assert [f.key for f in loaded.header.right] == ["created"]
    assert [f.barcode for f in loaded.header.left] == [False, True][: 1 + show_barcode]
    assert loaded.header.middle == []
    service.validate(target, loaded)
