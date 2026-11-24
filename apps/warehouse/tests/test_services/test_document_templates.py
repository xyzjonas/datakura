import pytest

from apps.warehouse.core.exceptions import NotFoundException, TemplateRenderError
from apps.warehouse.core.services.document_templates import (
    TARGETS,
    date_filter,
    document_template_service as service,
    money_filter,
    number_filter,
)
from apps.warehouse.models.document_template import DocumentTarget, DocumentTemplate
from apps.warehouse.tests.factories.customer import CustomerFactory
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

# variable under which each target exposes its record's `code`
CODE_VARIABLE = {
    DocumentTarget.GOODS_RECEIPT: "receipt.code",
    DocumentTarget.ISSUE_NOTE: "issue_note.code",
    DocumentTarget.DELIVERY_NOTE: "order.code",
    DocumentTarget.OUTBOUND_INVOICE: "invoice.code",
    DocumentTarget.OFFER: "offer.code",
}


@pytest.fixture
def records(db) -> dict[DocumentTarget, str]:
    """One printable record per target -> its code."""
    customer = CustomerFactory(name="ACME <b>s.r.o.</b>")
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


def test_every_target_has_a_default_template_and_spec() -> None:
    assert set(TARGETS) == set(DocumentTarget)
    for target in DocumentTarget:
        assert service.get_default_content(target).strip().startswith("<!DOCTYPE html>")


@pytest.mark.parametrize("target", list(DocumentTarget))
def test_default_template_renders_over_a_real_record(records, target) -> None:
    code = records[target]

    html = service.render_record_html(target, code)

    assert code in html
    assert "<html" in html


@pytest.mark.parametrize("target", list(DocumentTarget))
def test_draft_content_overrides_the_saved_template(records, target) -> None:
    code = records[target]
    DocumentTemplate.objects.create(target=target, content="saved")

    draft = service.render_record_html(
        target, code, "{{ " + CODE_VARIABLE[target] + " }}"
    )
    saved = service.render_record_html(target, code)

    assert draft == code
    assert saved == "saved"


@pytest.mark.parametrize("key", ["items", "values", "keys", "get", "update"])
def test_dict_keys_win_over_dict_methods(key) -> None:
    assert (
        service.render_html("{{ data." + key + " }}", {"data": {key: "field"}})
        == "field"
    )


def test_context_values_are_autoescaped(records) -> None:
    html = service.render_record_html(
        DocumentTarget.DELIVERY_NOTE,
        records[DocumentTarget.DELIVERY_NOTE],
        "{{ order.customer.name }}",
    )

    assert "<b>" not in html
    assert "&lt;b&gt;" in html


@pytest.mark.parametrize(
    "source",
    [
        "{{ ''.__class__.__mro__ }}",
        "{{ ''.__class__.__mro__[1].__subclasses__() }}",
        "{{ cycler.__init__.__globals__ }}",
        "{{ lipsum.__globals__ }}",
        "{{ order.__class__ }}",
    ],
)
def test_sandbox_blocks_python_internals(source) -> None:
    with pytest.raises(TemplateRenderError):
        service.render_html(source, {"order": {"code": "X"}})


@pytest.mark.parametrize(
    "source, line",
    [
        ("{{ unclosed", 1),
        ("ok\n{% if x %}\nnever closed", 2),  # reported at the unclosed block
        ("a\nb\n{% endfor %}", 3),
        ("{{ 1 | nonexistent_filter }}", 1),
    ],
)
def test_broken_template_raises_with_line(source, line) -> None:
    with pytest.raises(TemplateRenderError) as e:
        service.render_html(source, {})

    assert e.value.line == line
    assert f"line {line}" in str(e.value)


def test_runtime_error_reports_template_line() -> None:
    with pytest.raises(TemplateRenderError) as e:
        service.render_html("one\ntwo\n{{ 1 / 0 }}", {})

    assert e.value.line == 3
    assert "ZeroDivisionError" in e.value.reason


@pytest.mark.parametrize(
    "source", ["{{ nope }}", "{{ a.b.c.d }}", "{{ order.nope.x }}"]
)
def test_missing_variables_render_empty(source) -> None:
    assert service.render_html(source, {"order": {}}) == ""


@pytest.mark.parametrize(
    "value, fmt, expected",
    [
        (None, "d. m. Y", ""),
        ("", "d. m. Y", ""),
        ("not a date", "d. m. Y", ""),
        ("2026-03-05", "d. m. Y", "05. 03. 2026"),
        ("2026-03-05T10:00:00+00:00", "Y-m-d", "2026-03-05"),
    ],
)
def test_date_filter(value, fmt, expected) -> None:
    assert date_filter(value, fmt) == expected


@pytest.mark.parametrize(
    "value, decimals, expected",
    [(None, 2, ""), ("", 2, ""), (1.005, 2, "1,01"), (3, 0, "3"), (2.5, 4, "2,5000")],
)
def test_number_filter(value, decimals, expected) -> None:
    assert number_filter(value, decimals) in {expected, expected.replace(",", ".")}


def test_money_filter() -> None:
    assert money_filter(None, "CZK") == ""
    assert money_filter(10, "CZK").endswith(" CZK")
    assert "CZK" not in money_filter(10)


def test_get_content_falls_back_to_default_then_saved() -> None:
    target = DocumentTarget.OFFER

    content, is_default = service.get_content(target)
    assert is_default
    assert content == service.get_default_content(target)

    service.save_template(target, "<p>mine</p>")
    assert service.get_content(target) == ("<p>mine</p>", False)

    service.save_template(target, "<p>mine v2</p>")
    assert DocumentTemplate.objects.filter(target=target).count() == 1
    assert service.get_content(target) == ("<p>mine v2</p>", False)


def test_reset_restores_default() -> None:
    target = DocumentTarget.ISSUE_NOTE
    service.save_template(target, "<p>mine</p>")

    template = service.reset_template(target)

    assert template.is_default
    assert template.content == service.get_default_content(target)
    assert not DocumentTemplate.objects.filter(target=target).exists()


@pytest.mark.parametrize("content", ["", "   \n  ", "{% if %}", "{{ oops"])
def test_save_rejects_empty_and_uncompilable(content) -> None:
    with pytest.raises(TemplateRenderError):
        service.save_template(DocumentTarget.OFFER, content)

    assert not DocumentTemplate.objects.exists()


def test_save_keeps_template_source_verbatim() -> None:
    source = '<p class="x">{{ "<&>" }}</p>\n\t{# c #}'

    service.save_template(DocumentTarget.OFFER, source)

    assert service.get_content(DocumentTarget.OFFER)[0] == source


def test_list_targets_flags_customised(db) -> None:
    service.save_template(DocumentTarget.OFFER, "x")

    targets = {t.target: t for t in service.list_targets()}

    assert set(targets) == set(DocumentTarget)
    assert not targets[DocumentTarget.OFFER].is_default
    assert targets[DocumentTarget.OFFER].label == "Nabídka"
    assert targets[DocumentTarget.ISSUE_NOTE].is_default


@pytest.mark.parametrize(
    "target, paths",
    [
        (DocumentTarget.DELIVERY_NOTE, ["order.code", "order.items[].product.name"]),
        (DocumentTarget.OFFER, ["offer.customer.name", "offer.items[].unit_price"]),
        (DocumentTarget.ISSUE_NOTE, ["issue_note.order_items[].amount"]),
        (DocumentTarget.GOODS_RECEIPT, ["receipt.total_price_at_receipt"]),
        (
            DocumentTarget.OUTBOUND_INVOICE,
            [
                "invoice.code",
                "order_sections[].order.items[].total_price",
                "total_amount",
            ],
        ),
    ],
)
def test_legend_lists_context_paths(target, paths) -> None:
    legend = service.get_legend(target)

    available = {entry.path: entry for entry in legend.fields}
    for path in paths:
        assert path in available
    assert available[
        "order_sections" if target == DocumentTarget.OUTBOUND_INVOICE else paths[0]
    ]
    assert {"date", "number", "money", "default"} <= {f.name for f in legend.filters}


def test_legend_terminates_on_self_referencing_schemas() -> None:
    legend = service.get_legend(DocumentTarget.ISSUE_NOTE)

    assert any(e.path.startswith("issue_note.parent_order") for e in legend.fields)


def test_records_are_searchable(records) -> None:
    code = records[DocumentTarget.DELIVERY_NOTE]

    assert [
        r.code for r in service.list_records(DocumentTarget.DELIVERY_NOTE, code)
    ] == [code]
    assert service.list_records(DocumentTarget.DELIVERY_NOTE, "no-such-record") == []


@pytest.mark.parametrize("target", list(DocumentTarget))
def test_records_listed_for_every_target(records, target) -> None:
    listed = {r.code for r in service.list_records(target)}

    assert records[target] in listed


def test_unknown_target_is_not_found() -> None:
    with pytest.raises(NotFoundException):
        service.get_content("nonsense")  # type: ignore[arg-type]


def test_pdf_fetcher_refuses_local_files(tmp_path) -> None:
    try:
        from weasyprint.urls import URLFetcher  # type: ignore
    except OSError as e:
        pytest.skip(f"weasyprint system libraries missing: {e}")
    from apps.warehouse.core.services.pdf import ALLOWED_RESOURCE_PROTOCOLS

    secret = tmp_path / "secret.txt"
    secret.write_text("secret")
    fetcher = URLFetcher(allowed_protocols=ALLOWED_RESOURCE_PROTOCOLS)

    with pytest.raises(Exception):  # noqa: B017 - weasyprint's error type varies
        fetcher.fetch(secret.as_uri())
