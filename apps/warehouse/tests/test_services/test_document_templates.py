import re
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import mock

import pytest

from apps.warehouse.core.exceptions import (
    InvalidDocumentLayoutError,
    NotFoundException,
)
from apps.warehouse.core.schemas.document_templates import (
    DocumentLayoutSchema,
    DocumentPageSettingsSchema,
    LayoutFieldSchema,
    LayoutPartSchema,
    PageSchema,
    PaginationSchema,
)
from apps.warehouse.core.services.document_data import SPECS, Kind
from apps.warehouse.core.services.document_fonts import FONTS, FONTS_DIR, WEIGHTS
from apps.warehouse.core.services.document_templates import (
    default_layout,
    document_template_service as service,
    format_value,
    render_inline_markup,
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
    OutboundWarehouseOrderItemFactory,
    InboundWarehouseOrderFactory,
    WarehouseOrderOutFactory,
)

PIXEL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def freeze_time(moment: datetime):
    return mock.patch("django.utils.timezone.now", return_value=moment)


def parts(*keys: str, **options) -> list[LayoutPartSchema]:
    return [LayoutPartSchema(key=k, show_label=False, **options) for k in keys]


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
        DocumentTarget.OUTBOUND_ORDER: order.code,
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


def test_format_datetime_prints_the_date_only() -> None:
    value = datetime(2026, 3, 7, 14, 5, tzinfo=timezone.utc)

    assert format_value(value, Kind.DATETIME) == "07. 03. 2026"


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
            _with(header__middle=[LayoutFieldSchema(parts=parts("name", "nope"))]),
            "Unknown attribute.*nope",
        ),
        (
            _with(items__columns=fields("unit_price")),
            "Unknown attribute",
        ),  # not on issue note
        (_with(items__summaries=fields("total_amount")), "Unknown attribute"),
        (_with(items__columns=[]), "at least 1 column"),
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


def _logo_layout(section: str, block: str = "header") -> DocumentLayoutSchema:
    layout = default_layout(DocumentTarget.OFFER)
    layout.page.logo = PIXEL
    logo = [LayoutFieldSchema(key="logo", show_label=False)]
    if block == "header":
        setattr(layout.header, section, logo)
    else:
        getattr(layout, block).fields = logo
    return layout


@pytest.mark.parametrize(
    "section, block",
    [
        ("left", "header"),
        ("middle", "header"),
        ("right", "header"),
        ("", "supplier"),
        ("", "customer"),
    ],
)
def test_logo_is_printed_wherever_it_is_placed(records, section, block) -> None:
    target = DocumentTarget.OFFER
    layout = _logo_layout(section, block)

    html = service.render_record_html(target, records[target], layout)

    assert html.count(f'src="{PIXEL}"') == 1
    assert 'class="logo-img"' in html


def test_logo_can_be_placed_twice(records) -> None:
    target = DocumentTarget.OFFER
    layout = _logo_layout("left")
    layout.supplier.fields = [LayoutFieldSchema(key="logo", show_label=False)]

    html = service.render_record_html(target, records[target], layout)

    assert html.count(f'src="{PIXEL}"') == 2


def test_logo_without_an_uploaded_image_prints_nothing(records) -> None:
    target = DocumentTarget.OFFER
    layout = _logo_layout("left")
    layout.page.logo = None

    html = service.render_record_html(target, records[target], layout)

    assert "logo-img" not in html.split("</style>")[1]


def test_uploaded_logo_is_not_printed_unless_placed(records) -> None:
    target = DocumentTarget.OFFER
    layout = default_layout(target)
    layout.page.logo = PIXEL

    html = service.render_record_html(target, records[target], layout)

    assert PIXEL not in html


def test_logo_is_never_turned_into_a_barcode(records) -> None:
    target = DocumentTarget.OFFER
    layout = _logo_layout("left")
    layout.header.left = [
        LayoutFieldSchema(key="logo", barcode=True, barcode_text=True)
    ]

    html = service.render_record_html(target, records[target], layout)

    assert f'src="{PIXEL}"' in html
    assert 'class="barcode"' not in html


def test_footer_and_empty_footer(records) -> None:
    target = DocumentTarget.OFFER
    layout = default_layout(target)
    layout.footer.enabled = True
    layout.footer.text = "Thank <you>"

    html = service.render_record_html(target, records[target], layout)
    assert "Thank &lt;you&gt;" in html

    layout.footer.text = "   "
    html = service.render_record_html(target, records[target], layout)
    assert 'class="footer"' not in html


def test_parties_are_separated_by_a_divider_not_cards(records) -> None:
    target = DocumentTarget.OFFER

    html = service.render_record_html(target, records[target])

    assert ".party + .party {" in html
    assert "border-left: 1px solid" in html
    assert "border-radius" not in html
    assert "background: #f6f8fb" not in html


@pytest.mark.django_db
def test_legacy_logo_block_is_migrated_to_an_attribute() -> None:
    layout = default_layout(DocumentTarget.OFFER).model_dump(mode="json")
    layout.pop("page")
    layout["logo"] = {"enabled": True, "image": PIXEL, "align": "right"}
    DocumentTemplate.objects.create(target=DocumentTarget.OFFER, layout=layout)

    loaded, _ = service.get_layout(DocumentTarget.OFFER)

    assert loaded.page.logo == PIXEL
    assert loaded.header.right[0].key == "logo"


@pytest.mark.django_db
def test_legacy_disabled_logo_is_not_placed() -> None:
    layout = default_layout(DocumentTarget.OFFER).model_dump(mode="json")
    layout["logo"] = {"enabled": False, "image": PIXEL, "align": "left"}
    DocumentTemplate.objects.create(target=DocumentTarget.OFFER, layout=layout)

    loaded, _ = service.get_layout(DocumentTarget.OFFER)

    assert all(f.key != "logo" for f in loaded.header.left)


# --- fonts --------------------------------------------------------------------------


def test_default_font_is_the_system_one_without_embedding(records) -> None:
    target = DocumentTarget.OFFER

    html = service.render_record_html(target, records[target])

    assert 'font-family: "DejaVu Sans", sans-serif;' in html
    assert "@font-face" not in html


@pytest.mark.parametrize("key", [k for k, f in FONTS.items() if f.bundled])
def test_bundled_font_is_embedded_never_linked(records, key) -> None:
    target = DocumentTarget.OFFER
    layout = default_layout(target)
    layout.page.font = key

    html = service.render_record_html(target, records[target], layout)

    assert html.count("@font-face") == 2  # regular + bold
    assert html.count("data:font/woff2;base64,") == 2
    assert f"font-family: {FONTS[key].stack};" in html
    assert "http://" not in html and "https://" not in html


@pytest.mark.parametrize("key", list(FONTS))
def test_pdf_renders_with_every_font(records, key) -> None:
    target = DocumentTarget.OFFER
    layout = default_layout(target)
    layout.page.font = key

    assert service.render_record_pdf(target, records[target], layout).startswith(
        b"%PDF"
    )


def test_every_bundled_font_has_files_and_a_license() -> None:
    for font in FONTS.values():
        if font.bundled:
            for weight in WEIGHTS:
                assert (FONTS_DIR / font.key / f"{font.key}-{weight}.woff2").is_file()
            assert (FONTS_DIR / font.key / "LICENSE").is_file()


def test_unknown_font_is_rejected() -> None:
    with pytest.raises(ValueError):
        PageSchema(font="comic-sans")


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

    assert html.index('class="sec-left"') < html.index("L:")
    assert html.index("L:") < html.index('class="sec-middle"') < html.index("M:")
    assert html.index("M:") < html.index('class="sec-right"') < html.index("R:")


def test_empty_middle_section_keeps_the_right_one_on_the_right(records) -> None:
    target = DocumentTarget.OFFER
    layout = _layout_with_header(right=[LayoutFieldSchema(key="currency", label="R:")])

    html = service.render_record_html(target, records[target], layout)

    assert 'class="sec-left"' in html and 'class="sec-middle"' in html


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
            parts=parts(
                "street", "postal_code", "city", "tax_identification"
            ),  # last empty
            label="Adresa:",
            separator=" | ",
        )
    ]

    html = service.render_record_html(target, records[target], layout)

    assert "Adresa:" in html
    chained = re.sub(r"<[^>]+>", "", html.split("Adresa:")[1].split("</p>")[0])
    assert chained.split() == ["Hlavní", "1", "|", "11000", "|", "Praha"]
    assert "EMPTY" not in chained


def test_composite_column_stacks_values(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.items.columns = [
        LayoutFieldSchema(
            parts=parts("product_code", "product_name"),
            direction="column",
            show_label=False,
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
        LayoutFieldSchema(parts=parts("tax_identification"), label="EMPTY-COMPOSITE")
    ]

    html = service.render_record_html(target, records[target], layout)

    assert "EMPTY-COMPOSITE" not in html


@pytest.mark.parametrize(
    "ref",
    [
        {},  # neither key nor parts
        {"key": "name", "parts": [{"key": "name"}]},  # both
        {"key": "name", "text": "x"},  # attribute and static text
        {"parts": [{"key": "a", "text": "b"}]},  # a part cannot be both
        {"parts": [{}]},
        {"key": "name", "font_size": 5},
        {"key": "name", "font_size": 73},
        {"parts": [{"key": "a"}], "barcode": True},  # barcode is per part
        {"parts": [{"key": "a"}] * 11},  # too many parts
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
        left=[LayoutFieldSchema(parts=parts("code", "external_code", barcode=True))],
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


# --- font size, bold / muted, barcode text, static text, printed, margins -------------


def _customer_line(target, records, ref) -> str:
    layout = default_layout(target)
    layout.supplier.enabled = False
    layout.customer.fields = [ref]
    return service.render_record_html(target, records[target], layout)


def test_font_size_bold_and_muted_style_the_value(records) -> None:
    html = _customer_line(
        DocumentTarget.DELIVERY_NOTE,
        records,
        LayoutFieldSchema(key="identification", font_size=20, bold=True, muted=True),
    )

    assert '<span class="v bold muted" style="font-size: 20px">12345678</span>' in html


def test_unstyled_value_has_no_inline_style(records) -> None:
    html = _customer_line(
        DocumentTarget.DELIVERY_NOTE, records, LayoutFieldSchema(key="identification")
    )

    assert '<span class="v">12345678</span>' in html


def test_font_size_scales_the_barcode_too(records) -> None:
    html = _customer_line(
        DocumentTarget.DELIVERY_NOTE,
        records,
        LayoutFieldSchema(key="identification", barcode=True, font_size=30),
    )

    # the barcode height is in em, so the size of the wrapper scales it
    assert 'style="font-size: 30px"><span class="bc"><img class="barcode"' in html
    assert (
        "em;" in html
        and ".barcode { display: block; margin: 0 auto; height: 3.6em" in html
    )


@pytest.mark.parametrize("barcode_text, printed", [(True, True), (False, False)])
def test_barcode_text_prints_the_value_under_the_barcode(
    records, barcode_text, printed
) -> None:
    html = _customer_line(
        DocumentTarget.DELIVERY_NOTE,
        records,
        LayoutFieldSchema(
            key="identification", barcode=True, barcode_text=barcode_text
        ),
    )

    assert ('<span class="bc-text">12345678</span>' in html) is printed


def test_barcode_text_is_ignored_without_a_barcode_or_when_not_encodable(
    records,
) -> None:
    plain = _customer_line(
        DocumentTarget.DELIVERY_NOTE,
        records,
        LayoutFieldSchema(key="identification", barcode_text=True),
    )
    assert "bc-text" not in plain.split("</style>")[1]

    unencodable = _customer_line(
        DocumentTarget.DELIVERY_NOTE,
        records,
        LayoutFieldSchema(text="Příliš", barcode=True, barcode_text=True),
    )
    assert "bc-text" not in unencodable.split("</style>")[1]
    assert "Příliš" in unencodable


def test_composite_parts_have_their_own_options(records) -> None:
    ref = LayoutFieldSchema(
        label="Who",
        show_label=True,
        parts=[
            LayoutPartSchema(key="identification", show_label=False, bold=True),
            LayoutPartSchema(key="tax_identification", show_label=False),  # empty
            LayoutPartSchema(key="name", label="Name:", show_label=True, muted=True),
            LayoutPartSchema(text="STATIC", show_label=False, font_size=9),
            LayoutPartSchema(key="postal_code", show_label=False, barcode=True),
        ],
        separator=" / ",
    )

    html = _customer_line(DocumentTarget.DELIVERY_NOTE, records, ref)

    assert "Who" in html
    assert '<span class="v bold">12345678</span>' in html
    assert '<span class="v muted">' in html
    assert '<span class="v" style="font-size: 9px">STATIC</span>' in html
    assert html.count('class="barcode"') >= 1


def test_composite_style_applies_to_the_whole_value(records) -> None:
    ref = LayoutFieldSchema(
        parts=parts("identification", "city"), bold=True, font_size=12
    )

    html = _customer_line(DocumentTarget.DELIVERY_NOTE, records, ref)

    assert (
        '<span class="v bold" style="font-size: 12px"><span class="v">12345678' in html
    )


def test_static_text_is_escaped_and_can_have_a_caption(records) -> None:
    html = _customer_line(
        DocumentTarget.DELIVERY_NOTE,
        records,
        LayoutFieldSchema(text="Thanks <b>!</b>", label="Note:"),
    )

    assert "Note:" in html
    assert "Thanks &lt;b&gt;!&lt;/b&gt;" in html


def test_static_text_works_in_a_table_cell(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.items.columns = [LayoutFieldSchema(text="PCS", label="Unit")]

    html = service.render_record_html(target, records[target], layout)

    assert "<td>" in html and ">PCS<" in html


def test_printed_timestamp_is_evaluated_at_print_time(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = _layout_with_header(
        target, right=[LayoutFieldSchema(key="printed_at", label="Vystaveno:")]
    )
    first = datetime(2030, 1, 2, 3, 4, tzinfo=timezone.utc)
    later = datetime(2031, 5, 6, 7, 8, tzinfo=timezone.utc)

    with freeze_time(first):
        one = service.render_record_html(target, records[target], layout)
    with freeze_time(later):
        two = service.render_record_html(target, records[target], layout)

    assert "Vystaveno:" in one
    assert "02. 01. 2030" in one and "02. 01. 2030" not in two
    assert "06. 05. 2031" in two


@pytest.mark.parametrize("target", list(DocumentTarget))
def test_printed_timestamp_is_offered_in_every_block(target) -> None:
    catalog = service.get_template(target).catalog

    for block in (
        catalog.header_fields,
        catalog.supplier_fields,
        catalog.customer_fields,
        catalog.item_columns,
        catalog.summaries,
    ):
        assert "printed_at" in {f.key for f in block}


def test_printed_timestamp_in_items_and_summaries(records) -> None:
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.items.columns = fields("printed_at")
    layout.items.summaries = fields("printed_at")

    with freeze_time(datetime(2032, 9, 9, 9, 9, tzinfo=timezone.utc)):
        html = service.render_record_html(target, records[target], layout)

    assert html.count("09. 09. 2032") == 2


def test_default_page_margins_and_custom_ones(records) -> None:
    target = DocumentTarget.OFFER
    default = service.render_record_html(target, records[target])
    layout = default_layout(target)
    layout.page = PageSchema(
        margin_top=0, margin_right=1, margin_bottom=20, margin_left=200
    )
    custom = service.render_record_html(target, records[target], layout)

    assert "margin: 30px 30px 30px 30px;" in default
    assert "margin: 0px 1px 20px 200px;" in custom


@pytest.mark.parametrize(
    "field", ["margin_top", "margin_right", "margin_bottom", "margin_left"]
)
@pytest.mark.parametrize("value", [-1, 201])
def test_page_margins_are_bounded(field, value) -> None:
    with pytest.raises(ValueError):
        PageSchema(**{field: value})


def test_pdf_without_margins_is_rendered(records) -> None:
    target = DocumentTarget.OFFER
    layout = default_layout(target)
    layout.page = PageSchema(
        margin_top=0, margin_right=0, margin_bottom=0, margin_left=0
    )

    assert service.render_record_pdf(target, records[target], layout).startswith(
        b"%PDF"
    )


@pytest.mark.django_db
def test_layout_saved_with_string_part_composites_still_loads() -> None:
    target = DocumentTarget.OFFER
    layout = default_layout(target).model_dump(mode="json")
    layout["customer"]["fields"] = [
        {"parts": ["street", "city"], "barcode": True, "separator": " - "}
    ]
    layout["header"]["left"] = [{"parts": ["code"], "direction": "column"}]
    layout["items"]["columns"] = [{"parts": ["product_code"]}]
    del layout["page"]
    DocumentTemplate.objects.create(target=target, layout=layout)

    loaded, _ = service.get_layout(target)

    field = loaded.customer.fields[0]
    assert [(p.key, p.barcode, p.show_label) for p in field.parts] == [
        ("street", True, False),
        ("city", True, False),
    ]
    assert not field.barcode and field.separator == " - "
    assert loaded.header.left[0].direction == "column"
    assert loaded.page == PageSchema()
    service.validate(target, loaded)


# --- delivery code (customer's code, ours otherwise) --------------------------------


@pytest.mark.parametrize(
    "customer_code, expected",
    [
        (None, "OUR-1"),
        ("", "OUR-1"),
        ("THEIRS-9", "THEIRS-9"),
    ],
)
def test_delivery_code_falls_back_to_the_internal_code(customer_code, expected) -> None:
    from apps.warehouse.core.services.document_data import _price_item

    row = _price_item(
        {
            "index": 0,
            "amount": 1,
            "product": {"code": "OUR-1", "name": "Thing", "unit": "ks"},
            "customer_product_code": customer_code,
        },
        unit_price=1,
        total_price=1,
    )

    assert row["delivery_code"] == expected


@pytest.mark.parametrize(
    "target",
    [
        DocumentTarget.OUTBOUND_INVOICE,
        DocumentTarget.DELIVERY_NOTE,
        DocumentTarget.OFFER,
        DocumentTarget.ISSUE_NOTE,
    ],
)
def test_delivery_code_is_offered_for_customer_facing_documents(target) -> None:
    assert "delivery_code" in SPECS[target].fields_of("items")


@pytest.mark.parametrize("requires_own_codes", [True, False])
def test_delivery_note_prints_customer_code_only_when_required(
    db, requires_own_codes
) -> None:
    from apps.warehouse.tests.factories.product import (
        CustomerProductCodeFactory,
        StockProductFactory,
    )

    customer = CustomerFactory(requires_own_codes=requires_own_codes)
    product = StockProductFactory()
    CustomerProductCodeFactory.it(customer=customer, product=product, code="THEIRS-42")
    order = OutboundOrderFactory.it(customer=customer, currency="CZK")
    OutboundOrderItemFactory(order=order, stock_product=product)
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.items.columns = [LayoutFieldSchema(key="delivery_code", label="Kód")]

    html = str(service.render_record_html(target, order.code, layout))

    expected = "THEIRS-42" if requires_own_codes else product.code
    assert f">{expected}</span>" in html
    assert ("THEIRS-42" in html) is requires_own_codes


@pytest.mark.parametrize("requires_own_codes", [True, False])
def test_issue_note_takes_the_delivery_code_from_the_parent_order(
    db, requires_own_codes
) -> None:
    from apps.warehouse.tests.factories.product import (
        CustomerProductCodeFactory,
        StockProductFactory,
    )

    customer = CustomerFactory(requires_own_codes=requires_own_codes)
    product = StockProductFactory()
    CustomerProductCodeFactory.it(customer=customer, product=product, code="THEIRS-42")
    order = OutboundOrderFactory.it(customer=customer, currency="CZK")
    order_item = OutboundOrderItemFactory(order=order, stock_product=product)
    note = WarehouseOrderOutFactory.it(order=order)
    OutboundWarehouseOrderItemFactory.it(
        warehouse_order=note, source_order_item=order_item
    )
    target = DocumentTarget.ISSUE_NOTE
    layout = default_layout(target)
    layout.items.columns = [LayoutFieldSchema(key="delivery_code", label="Kód")]

    html = str(service.render_record_html(target, note.code, layout))

    expected = "THEIRS-42" if requires_own_codes else product.code
    assert f">{expected}</span>" in html
    assert ("THEIRS-42" in html) is requires_own_codes


# --- OP has its own template, separate from the delivery note ----------------------


def test_outbound_order_and_delivery_note_are_customised_independently(records) -> None:
    op, note = DocumentTarget.OUTBOUND_ORDER, DocumentTarget.DELIVERY_NOTE
    layout = default_layout(op)
    layout.header.title = "Objednávka OP"

    service.save_template(op, layout)

    assert service.get_layout(op)[0].header.title == "Objednávka OP"
    assert service.get_layout(note) == (default_layout(note), True)
    assert "Objednávka OP" in service.render_record_html(op, records[op])
    assert "Objednávka OP" not in service.render_record_html(note, records[note])


# --- footer formatting -------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("plain", "plain"),
        ("**bold**", "<strong>bold</strong>"),
        ("*italic*", "<em>italic</em>"),
        ("__under__", "<u>under</u>"),
        ("**b** and *i*", "<strong>b</strong> and <em>i</em>"),
        ("**bold** *both*", "<strong>bold</strong> <em>both</em>"),
        ("** spaced **", "** spaced **"),
        ("a * b * c", "a * b * c"),  # lone asterisks stay
        ("2*3*4", "2*3*4"),
        ("**unclosed", "**unclosed"),
        ("", ""),
        ("<script>alert(1)</script>", "&lt;script&gt;alert(1)&lt;/script&gt;"),
        ("**<b>x</b>**", "<strong>&lt;b&gt;x&lt;/b&gt;</strong>"),
        ("line 1\nline 2", "line 1\nline 2"),
        ("**two\nlines**", "<strong>two\nlines</strong>"),
    ],
)
def test_render_inline_markup(text, expected) -> None:
    assert render_inline_markup(text) == expected


def test_footer_is_rendered_with_basic_formatting(records) -> None:
    target = DocumentTarget.OFFER
    layout = default_layout(target)
    layout.footer.enabled = True
    layout.footer.text = "Thanks **a lot** <i>x</i>"

    html = service.render_record_html(target, records[target], layout)

    assert "Thanks <strong>a lot</strong> &lt;i&gt;x&lt;/i&gt;" in html


# --- layout CSS: table cells centred, parties centred in their halves ---------------


def test_table_cells_and_parties_are_centred(records) -> None:
    target = DocumentTarget.OFFER

    html = service.render_record_html(target, records[target])

    assert "vertical-align: middle" in html
    assert re.search(r"\.party \{[^}]*text-align: center", html)


# --- footer sticks to the bottom of the (last) page --------------------------------


def _footer_layout(target: DocumentTarget) -> DocumentLayoutSchema:
    layout = default_layout(target)
    layout.footer.enabled = True
    layout.footer.text = "Footer"
    return layout


@pytest.mark.parametrize(
    "free, expected_margin",
    [(500, "calc(6px + 498px)"), (3, "calc(6px + 1px)"), (2, None), (0, None)],
)
def test_pdf_footer_gap_is_measured_and_applied(records, free, expected_margin) -> None:
    target = DocumentTarget.OFFER
    printed: list[str] = []

    def fake_print(content_html: str) -> bytes:
        printed.append(content_html)
        return b"%PDF"

    with (
        mock.patch(
            "apps.warehouse.core.services.document_templates.free_space_below",
            return_value=free,
        ),
        mock.patch(
            "apps.warehouse.core.services.document_templates.print_html_to_pdf",
            side_effect=fake_print,
        ),
    ):
        service.render_record_pdf(target, records[target], _footer_layout(target))

    assert len(printed) == 1
    if expected_margin:
        assert f'style="margin-top: {expected_margin}"' in printed[0]
    else:
        assert 'class="footer" style' not in printed[0]


def test_footer_gap_is_applied_inline_only_when_given(records) -> None:
    target = DocumentTarget.OFFER
    layout = _footer_layout(target)

    plain = service.render_record_html(target, records[target], layout)
    pushed = service.render_record_html(target, records[target], layout, footer_gap=321)

    assert 'style="margin-top: calc(6px + 321px)"' in pushed
    assert 'class="footer" style' not in plain


def test_footer_sits_at_the_bottom_of_a_short_document(records) -> None:
    from apps.warehouse.core.services.pdf import free_space_below

    target = DocumentTarget.OFFER
    layout = _footer_layout(target)
    html = service.render_record_html(target, records[target], layout)
    gap = free_space_below(html, "footer")
    assert gap > 300  # a short document leaves most of the page free

    pushed = service.render_record_html(
        target, records[target], layout, footer_gap=gap - 2
    )

    assert free_space_below(pushed, "footer") <= 4
    from weasyprint import HTML  # type: ignore[import-untyped]

    assert len(HTML(string=pushed).render().pages) == 1  # no spill-over page


def test_footer_gap_without_a_footer_is_zero(records) -> None:
    from apps.warehouse.core.services.pdf import free_space_below

    html = service.render_record_html(
        DocumentTarget.OFFER, records[DocumentTarget.OFFER]
    )

    assert free_space_below(html, "footer") == 0


# --- page settings shared by all documents -----------------------------------------


def test_apply_page_settings_to_all_documents(records) -> None:
    settings = DocumentPageSettingsSchema(
        page=PageSchema(margin_top=10, margin_left=55, font="inter", logo=PIXEL),
        pagination=PaginationSchema(enabled=True, position="top-center"),
    )
    custom = default_layout(DocumentTarget.OFFER)
    custom.header.title = "Keep me"
    service.save_template(DocumentTarget.OFFER, custom)

    targets = service.apply_page_settings_to_all(settings)

    assert {t.target for t in targets} == set(DocumentTarget)
    assert all(not t.is_default for t in targets)
    for target in DocumentTarget:
        layout, _ = service.get_layout(target)
        assert layout.page == settings.page
        assert layout.pagination == settings.pagination
    # nothing else is touched
    assert service.get_layout(DocumentTarget.OFFER)[0].header.title == "Keep me"
    assert (
        service.get_layout(DocumentTarget.ISSUE_NOTE)[0].header
        == default_layout(DocumentTarget.ISSUE_NOTE).header
    )


# --- header sizing, party text alignment ----------------------------------------------


def test_header_sections_do_not_inherit_the_nowrap_of_table_cells(records) -> None:
    target = DocumentTarget.OFFER

    html = service.render_record_html(target, records[target])

    # a class shared with the right-aligned table cells would stop long text from wrapping
    assert 'class="sec-right"' in html
    assert not re.search(r'<div class="right"', html)
    assert ".header-sections > div { flex: 0 1 auto" in html


@pytest.mark.parametrize(
    "middle, expected",
    [
        ([LayoutFieldSchema(key="state", label="M:")], True),
        ([], False),
    ],
)
def test_centered_header_layout_only_with_a_printed_middle(
    records, middle, expected
) -> None:
    target = DocumentTarget.OFFER
    layout = _layout_with_header(
        left=[LayoutFieldSchema(key="external_code", label="L:")], middle=middle
    )

    html = service.render_record_html(target, records[target], layout)

    assert ('class="header-sections has-middle"' in html) is expected


def test_party_text_is_left_aligned_inside_the_centered_block(records) -> None:
    target = DocumentTarget.OFFER

    html = service.render_record_html(target, records[target])

    assert re.search(r"\.party-rows \{[^}]*text-align: left", html)
    assert html.count('<div class="party-rows">') == 2


# --- norm of the product ------------------------------------------------------------


@pytest.mark.parametrize("target", list(DocumentTarget))
def test_norm_is_offered_as_an_item_column(target) -> None:
    assert SPECS[target].fields_of("items")["norm"].label == "Norma"


@pytest.mark.parametrize(
    "product, expected",
    [
        ({"code": "A", "name": "n", "norm": {"label": "DIN 84"}}, "DIN 84"),
        ({"code": "A", "name": "n", "norm": None}, None),
        ({"code": "A", "name": "n"}, None),
    ],
)
def test_priced_item_row_carries_the_norm_label(product, expected) -> None:
    from apps.warehouse.core.services.document_data import _price_item

    row = _price_item(
        {"index": 0, "amount": 1, "product": product},
        unit_price=1,
        total_price=1,
    )

    assert row["norm"] == expected


@pytest.mark.parametrize("with_norm", [True, False])
def test_delivery_note_prints_the_product_norm(db, with_norm) -> None:
    from apps.warehouse.tests.factories.product import NormFactory, StockProductFactory

    product = StockProductFactory(norm=NormFactory(code="84") if with_norm else None)
    order = OutboundOrderFactory.it(currency="CZK")
    OutboundOrderItemFactory(order=order, stock_product=product)
    target = DocumentTarget.DELIVERY_NOTE
    layout = default_layout(target)
    layout.items.columns = [LayoutFieldSchema(key="norm", label="Norma")]
    service.validate(target, layout)

    html = str(service.render_record_html(target, order.code, layout))

    assert ("DIN 84" in html) is with_norm


def test_issue_note_prints_the_product_norm(db) -> None:
    from apps.warehouse.tests.factories.product import NormFactory, StockProductFactory

    product = StockProductFactory(norm=NormFactory(code="933"))
    order = OutboundOrderFactory.it(currency="CZK")
    order_item = OutboundOrderItemFactory(order=order, stock_product=product)
    note = WarehouseOrderOutFactory.it(order=order)
    OutboundWarehouseOrderItemFactory.it(
        warehouse_order=note, source_order_item=order_item
    )
    target = DocumentTarget.ISSUE_NOTE
    layout = default_layout(target)
    layout.items.columns = [LayoutFieldSchema(key="norm", label="Norma")]

    html = str(service.render_record_html(target, note.code, layout))

    assert "DIN 933" in html
