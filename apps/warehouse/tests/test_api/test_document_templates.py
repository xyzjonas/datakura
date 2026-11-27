from typing import cast

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.warehouse.core.services.document_templates import default_layout
from apps.warehouse.models.document_template import DocumentTarget, DocumentTemplate
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.order import (
    InvoiceFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.user import UserFactory

URL = "/api/v1/document-templates"
PIXEL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def admin_client(db) -> Client:
    client = Client()
    client.force_login(cast(User, UserFactory(superuser=True)))
    return client


@pytest.fixture
def invoice_code(db) -> str:
    customer = CustomerFactory(name="ACME s.r.o.")
    invoice = InvoiceFactory.it(customer=customer, currency="CZK")
    order = OutboundOrderFactory.it(customer=customer, currency="CZK", invoice=invoice)
    OutboundOrderItemFactory(order=order, total_price=100, unit_price=100)
    return invoice.code


def _send(client: Client, method: str, url: str, body: dict | None = None):
    return getattr(client, method)(
        url, data=body or {}, content_type="application/json"
    )


def _layout(target: str = "offer") -> dict:
    return default_layout(DocumentTarget(target)).model_dump(mode="json")


# --- permissions -------------------------------------------------------------


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", ""),
        ("get", "/offer"),
        ("put", "/offer"),
        ("delete", "/offer"),
        ("get", "/offer/records"),
        ("post", "/offer/preview"),
        ("post", "/offer/pdf"),
        ("post", "/apply-page"),
    ],
)
def test_anonymous_is_unauthorized(db, method, path) -> None:
    assert _send(Client(), method, f"{URL}{path}").status_code == 401


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", ""),
        ("put", "/offer"),
        ("delete", "/offer"),
        ("post", "/offer/pdf"),
        ("post", "/apply-page"),
    ],
)
def test_regular_user_is_forbidden(db, method, path) -> None:
    client = Client()
    client.force_login(cast(User, UserFactory()))

    assert _send(client, method, f"{URL}{path}").status_code == 403


# --- targets / get / save / reset ----------------------------------------------


def test_list_targets(admin_client) -> None:
    data = admin_client.get(URL).json()["data"]

    assert {t["target"] for t in data} == {t.value for t in DocumentTarget}
    assert all(t["is_default"] for t in data)


@pytest.mark.parametrize("target", [t.value for t in DocumentTarget])
def test_get_returns_default_layout_and_catalog(admin_client, target) -> None:
    response = admin_client.get(f"{URL}/{target}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_default"] is True
    assert data["layout"] == _layout(target)
    catalog = data["catalog"]
    assert {f["key"] for f in catalog["supplier_fields"]} >= {"name", "identification"}
    assert "code" in {f["key"] for f in catalog["header_fields"]}
    has_contact = "contact_name" in {f["key"] for f in catalog["customer_fields"]}
    assert has_contact is (
        target in {"offer", "outbound_order", "delivery_note", "issue_note"}
    )
    assert not any(f["key"].startswith("contact_") for f in catalog["supplier_fields"])
    # the default layout only uses attributes the catalog offers
    offered = {f["key"] for f in catalog["item_columns"]}
    assert {c["key"] for c in data["layout"]["items"]["columns"]} <= offered


def test_get_unknown_target_is_a_validation_error(admin_client) -> None:
    assert admin_client.get(f"{URL}/nope").status_code == 422


def test_save_get_and_reset(admin_client) -> None:
    layout = _layout()
    layout["items"]["columns"] = [{"key": "product_name", "label": "Zboží"}]
    layout["footer"] = {"enabled": True, "text": "Díky"}

    saved = _send(admin_client, "put", f"{URL}/offer", {"layout": layout})
    assert saved.status_code == 200
    assert saved.json()["data"]["is_default"] is False

    loaded = admin_client.get(f"{URL}/offer").json()["data"]
    assert [c["key"] for c in loaded["layout"]["items"]["columns"]] == ["product_name"]
    assert loaded["layout"]["items"]["columns"][0]["label"] == "Zboží"
    assert loaded["layout"]["footer"] == {"enabled": True, "text": "Díky"}
    other = admin_client.get(f"{URL}/delivery_note").json()["data"]
    assert other["is_default"] is True

    reset = admin_client.delete(f"{URL}/offer")
    assert reset.status_code == 200
    assert reset.json()["data"]["is_default"] is True
    assert not DocumentTemplate.objects.exists()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda layout: layout["header"].update(left=[{"key": "bogus"}]),
        lambda layout: layout["header"].update(
            middle=[{"parts": [{"key": "name"}, {"key": "bogus"}]}]
        ),
        lambda layout: layout["header"].update(right=[{}]),  # key nor parts
        lambda layout: layout["header"].update(
            right=[{"key": "a", "parts": [{"key": "b"}]}]
        ),
        lambda layout: layout["supplier"].update(fields=[{"key": "contact_name"}]),
        lambda layout: layout["pagination"].update(position="middle"),
        lambda layout: layout["items"].update(columns=[]),
        lambda layout: layout["items"].update(summaries=[{"key": "nope"}]),
        lambda layout: layout["page"].update(font="comic-sans"),
    ],
    ids=[
        "unknown-key",
        "unknown-composite-part",
        "no-key-no-parts",
        "key-and-parts",
        "contact-on-supplier",
        "bad-page-number-position",
        "no-columns",
        "unknown-summary",
        "unknown-font",
    ],
)
def test_invalid_layout_is_not_saved(admin_client, mutate) -> None:
    layout = _layout()
    mutate(layout)

    response = _send(admin_client, "put", f"{URL}/offer", {"layout": layout})

    assert response.status_code == 422
    assert not DocumentTemplate.objects.exists()


@pytest.mark.parametrize(
    "image",
    [
        "https://example.com/logo.png",
        "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=",
        "data:text/html;base64,PGI+",
        "file:///etc/passwd",
        "data:image/png;base64," + "A" * 700_001,
    ],
    ids=["remote", "svg", "html", "file", "too-large"],
)
def test_logo_must_be_a_small_raster_data_url(admin_client, image) -> None:
    layout = _layout()
    layout["page"]["logo"] = image

    response = _send(admin_client, "put", f"{URL}/offer", {"layout": layout})

    assert response.status_code == 422


def test_label_length_and_field_count_limits(admin_client) -> None:
    layout = _layout()
    layout["header"]["title"] = "x" * 101

    assert (
        _send(admin_client, "put", f"{URL}/offer", {"layout": layout}).status_code
        == 422
    )


def test_save_with_valid_logo(admin_client) -> None:
    layout = _layout()
    layout["page"]["logo"] = PIXEL
    layout["header"]["right"] = [{"key": "logo", "show_label": False}]

    response = _send(admin_client, "put", f"{URL}/offer", {"layout": layout})

    assert response.status_code == 200
    assert response.json()["data"]["layout"]["page"]["logo"] == PIXEL


@pytest.mark.parametrize("block", ["header", "supplier", "customer"])
def test_logo_is_selectable_in_every_party_and_header_block(
    admin_client, block
) -> None:
    template = admin_client.get(f"{URL}/offer").json()["data"]

    assert "logo" in {f["key"] for f in template["catalog"][f"{block}_fields"]}


@pytest.mark.parametrize("block", ["item_columns", "summaries"])
def test_logo_is_not_offered_in_the_items_table(admin_client, block) -> None:
    template = admin_client.get(f"{URL}/offer").json()["data"]

    assert "logo" not in {f["key"] for f in template["catalog"][block]}


def test_catalog_lists_bundled_fonts_and_default_page_is_30px(admin_client) -> None:
    template = admin_client.get(f"{URL}/offer").json()["data"]

    fonts = {f["key"] for f in template["catalog"]["fonts"]}
    assert {"system", "roboto", "open-sans", "inter", "lato"} <= fonts
    page = template["layout"]["page"]
    assert [page[f"margin_{s}"] for s in ("top", "right", "bottom", "left")] == [30] * 4
    assert page["font"] == "system"


# --- records / preview / pdf -----------------------------------------------------


def test_records_search(admin_client, invoice_code) -> None:
    found = admin_client.get(f"{URL}/outbound_invoice/records").json()["data"]
    assert invoice_code in [r["code"] for r in found]

    filtered = admin_client.get(
        f"{URL}/outbound_invoice/records", {"q": "zzz-nothing"}
    ).json()["data"]
    assert filtered == []


def test_preview_renders_the_draft_layout(admin_client, invoice_code) -> None:
    layout = _layout("outbound_invoice")
    layout["header"]["title"] = "Draft invoice"

    response = _send(
        admin_client,
        "post",
        f"{URL}/outbound_invoice/preview",
        {"record_code": invoice_code, "layout": layout},
    )

    assert response.status_code == 200
    html = response.json()["data"]
    assert "Draft invoice" in html and invoice_code in html
    assert not DocumentTemplate.objects.exists()


def test_preview_without_a_layout_uses_the_saved_one(
    admin_client, invoice_code
) -> None:
    layout = _layout("outbound_invoice")
    layout["header"]["title"] = "Saved invoice"
    _send(admin_client, "put", f"{URL}/outbound_invoice", {"layout": layout})

    html = _send(
        admin_client,
        "post",
        f"{URL}/outbound_invoice/preview",
        {"record_code": invoice_code},
    ).json()["data"]

    assert "Saved invoice" in html


def test_preview_of_an_invalid_draft_is_rejected(admin_client, invoice_code) -> None:
    layout = _layout("outbound_invoice")
    layout["items"]["columns"] = [{"key": "nope"}]

    response = _send(
        admin_client,
        "post",
        f"{URL}/outbound_invoice/preview",
        {"record_code": invoice_code, "layout": layout},
    )

    assert response.status_code == 422


def test_pdf_of_the_draft(admin_client, invoice_code) -> None:
    response = _send(
        admin_client,
        "post",
        f"{URL}/outbound_invoice/pdf",
        {"record_code": invoice_code, "layout": _layout("outbound_invoice")},
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert invoice_code in response["Content-Disposition"]


def test_invoice_pdf_endpoint_uses_the_saved_layout(admin_client, invoice_code) -> None:
    layout = _layout("outbound_invoice")
    layout["header"]["title"] = "Saved invoice"
    _send(admin_client, "put", f"{URL}/outbound_invoice", {"layout": layout})

    html = admin_client.get(f"/api/v1/invoices/{invoice_code}/html")

    assert html.status_code == 200
    assert "Saved invoice" in html.content.decode()


def test_composite_barcode_and_pagination_round_trip_and_render(
    admin_client, invoice_code
) -> None:
    layout = _layout("outbound_invoice")
    layout["header"]["middle"] = [
        {
            "parts": [{"key": "issued_date"}, {"key": "due_date", "bold": True}],
            "direction": "column",
            "label": "Dates",
            "show_label": False,
        }
    ]
    layout["items"]["columns"] = [
        {"key": "product_code", "barcode": True, "show_label": False}
    ]
    layout["pagination"] = {"enabled": True, "position": "top-right"}

    saved = _send(admin_client, "put", f"{URL}/outbound_invoice", {"layout": layout})
    assert saved.status_code == 200
    loaded = admin_client.get(f"{URL}/outbound_invoice").json()["data"]["layout"]
    assert [p["key"] for p in loaded["header"]["middle"][0]["parts"]] == [
        "issued_date",
        "due_date",
    ]
    assert loaded["header"]["middle"][0]["parts"][1]["bold"] is True
    assert loaded["header"]["middle"][0]["direction"] == "column"
    assert loaded["items"]["columns"][0]["barcode"] is True
    assert loaded["pagination"] == {"enabled": True, "position": "top-right"}

    html = _send(
        admin_client,
        "post",
        f"{URL}/outbound_invoice/preview",
        {"record_code": invoice_code},
    ).json()["data"]
    assert "@top-right { content: counter(page)" in html
    assert 'class="barcode"' in html.split("<tbody>")[1]


def test_styling_static_text_and_margins_round_trip(admin_client, invoice_code) -> None:
    layout = _layout("outbound_invoice")
    layout["header"]["right"] = [
        {"key": "printed_at", "label": "Vystaveno:", "bold": True, "muted": True},
        {"text": "Hello", "font_size": 20},
        {"key": "code", "barcode": True, "barcode_text": True, "font_size": 30},
    ]
    layout["page"] = {
        "margin_top": 0,
        "margin_right": 0,
        "margin_bottom": 0,
        "margin_left": 0,
    }

    assert (
        _send(
            admin_client, "put", f"{URL}/outbound_invoice", {"layout": layout}
        ).status_code
        == 200
    )
    loaded = admin_client.get(f"{URL}/outbound_invoice").json()["data"]["layout"]
    assert loaded["page"] == {**layout["page"], "font": "system", "logo": None}
    right = loaded["header"]["right"]
    assert right[0]["bold"] and right[0]["muted"]
    assert right[1]["text"] == "Hello" and right[1]["font_size"] == 20
    assert right[2]["barcode_text"] is True

    html = _send(
        admin_client,
        "post",
        f"{URL}/outbound_invoice/preview",
        {"record_code": invoice_code},
    ).json()["data"]
    assert "margin: 0px 0px 0px 0px;" in html
    assert "Vystaveno:" in html and "Hello" in html and "bc-text" in html


@pytest.mark.parametrize(
    "mutate",
    [
        lambda layout: layout["page"].update(margin_top=-1),
        lambda layout: layout["page"].update(margin_left=201),
        lambda layout: layout["header"].update(right=[{"key": "code", "font_size": 3}]),
        lambda layout: layout["header"].update(right=[{"text": ""}]),
    ],
    ids=["negative-margin", "huge-margin", "tiny-font", "empty-static-text"],
)
def test_invalid_styling_is_rejected(admin_client, mutate) -> None:
    layout = _layout()
    mutate(layout)

    response = _send(admin_client, "put", f"{URL}/offer", {"layout": layout})

    assert response.status_code == 422


# --- page settings shared by all documents ---------------------------------------


def _page_settings(**page) -> dict:
    layout = _layout()
    return {"page": {**layout["page"], **page}, "pagination": layout["pagination"]}


def test_apply_page_settings_to_all(admin_client) -> None:
    body = _page_settings(margin_top=12, font="inter", logo=PIXEL)
    body["pagination"] = {"enabled": True, "position": "top-left"}

    response = _send(admin_client, "post", f"{URL}/apply-page", body)

    assert response.status_code == 200
    data = response.json()["data"]
    assert {t["target"] for t in data} == {t.value for t in DocumentTarget}
    assert all(t["is_default"] is False for t in data)
    for target in DocumentTarget:
        layout = admin_client.get(f"{URL}/{target.value}").json()["data"]["layout"]
        assert layout["page"]["margin_top"] == 12
        assert layout["page"]["font"] == "inter"
        assert layout["page"]["logo"] == PIXEL
        assert layout["pagination"] == {"enabled": True, "position": "top-left"}


@pytest.mark.parametrize(
    "page",
    [
        {"margin_top": -1},
        {"margin_left": 201},
        {"font": "comic-sans"},
        {"logo": "data:image/svg+xml;base64,AAAA"},
        {"logo": "not a data url"},
    ],
)
def test_apply_page_settings_validates(admin_client, page) -> None:
    response = _send(admin_client, "post", f"{URL}/apply-page", _page_settings(**page))

    assert response.status_code == 422
    assert DocumentTemplate.objects.count() == 0


def test_apply_page_settings_keeps_the_rest_of_the_layout(admin_client) -> None:
    layout = _layout("issue_note")
    layout["header"]["title"] = "Custom"
    _send(admin_client, "put", f"{URL}/issue_note", {"layout": layout})

    _send(admin_client, "post", f"{URL}/apply-page", _page_settings(margin_top=5))

    saved = admin_client.get(f"{URL}/issue_note").json()["data"]["layout"]
    assert saved["header"]["title"] == "Custom"
    assert saved["page"]["margin_top"] == 5


def test_outbound_order_target_is_served(admin_client) -> None:
    data = admin_client.get(f"{URL}/outbound_order").json()["data"]

    assert data["target"] == "outbound_order"
    assert data["is_default"] is True
    assert data["label"] == "Objednávka (OP)"
