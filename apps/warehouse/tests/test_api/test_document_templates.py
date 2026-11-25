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
    ],
)
def test_anonymous_is_unauthorized(db, method, path) -> None:
    assert _send(Client(), method, f"{URL}{path}").status_code == 401


@pytest.mark.parametrize(
    "method, path",
    [("get", ""), ("put", "/offer"), ("delete", "/offer"), ("post", "/offer/pdf")],
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
    assert {f["key"] for f in catalog["party_fields"]} >= {"name", "identification"}
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
    assert loaded["layout"]["items"]["columns"] == [
        {"key": "product_name", "label": "Zboží"}
    ]
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
        lambda layout: layout["header"].update(fields=[{"key": "bogus"}]),
        lambda layout: layout["items"].update(columns=[]),
        lambda layout: layout["items"].update(
            columns=[{"key": "amount"}, {"key": "amount"}]
        ),
        lambda layout: layout["items"].update(summaries=[{"key": "nope"}]),
        lambda layout: layout["logo"].update(enabled=True, image=None),
    ],
    ids=["unknown-key", "no-columns", "duplicate", "unknown-summary", "logo-no-image"],
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
    layout["logo"] = {"enabled": True, "image": image, "align": "left"}

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
    layout["logo"] = {"enabled": True, "image": PIXEL, "align": "center"}

    response = _send(admin_client, "put", f"{URL}/offer", {"layout": layout})

    assert response.status_code == 200
    assert response.json()["data"]["layout"]["logo"]["image"] == PIXEL


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
