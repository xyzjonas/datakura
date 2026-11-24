from typing import cast

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.warehouse.core.services.document_templates import document_template_service
from apps.warehouse.models.document_template import DocumentTarget, DocumentTemplate
from apps.warehouse.tests.factories.customer import CustomerFactory
from apps.warehouse.tests.factories.order import (
    InvoiceFactory,
    OutboundOrderFactory,
    OutboundOrderItemFactory,
)
from apps.warehouse.tests.factories.user import UserFactory

URL = "/api/v1/document-templates"


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
    response = admin_client.get(URL)

    assert response.status_code == 200
    data = response.json()["data"]
    assert {t["target"] for t in data} == {t.value for t in DocumentTarget}
    assert all(t["is_default"] for t in data)
    assert {t["target"]: t["label"] for t in data}["delivery_note"] == "Dodací list"


def test_get_default_template_includes_legend(admin_client) -> None:
    response = admin_client.get(f"{URL}/delivery_note")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["is_default"] is True
    assert data["content"] == document_template_service.get_default_content(
        DocumentTarget.DELIVERY_NOTE
    )
    assert "order.code" in {f["path"] for f in data["legend"]["fields"]}
    assert "date" in {f["name"] for f in data["legend"]["filters"]}


def test_update_then_get_custom_template(admin_client) -> None:
    response = _send(
        admin_client, "put", f"{URL}/offer", {"content": "<p>{{ offer.code }}</p>"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["is_default"] is False
    again = admin_client.get(f"{URL}/offer").json()["data"]
    assert again["content"] == "<p>{{ offer.code }}</p>"
    assert not {t["target"]: t for t in admin_client.get(URL).json()["data"]}["offer"][
        "is_default"
    ]


def test_reset_template(admin_client) -> None:
    DocumentTemplate.objects.create(target=DocumentTarget.OFFER, content="custom")

    response = admin_client.delete(f"{URL}/offer")

    assert response.status_code == 200
    assert response.json()["data"]["is_default"] is True
    assert not DocumentTemplate.objects.exists()


def test_reset_without_customisation_is_fine(admin_client) -> None:
    assert admin_client.delete(f"{URL}/offer").status_code == 200


@pytest.mark.parametrize(
    "content, status",
    [("", 422), ("   ", 422), ("{% if %}", 422), ("{{ x", 422)],
)
def test_update_rejects_bad_content(admin_client, content, status) -> None:
    response = _send(admin_client, "put", f"{URL}/offer", {"content": content})

    assert response.status_code == status
    assert response.json()["success"] is False
    assert not DocumentTemplate.objects.exists()


def test_update_missing_content_is_validation_error(admin_client) -> None:
    assert _send(admin_client, "put", f"{URL}/offer", {}).status_code == 422


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_unknown_target_is_rejected(admin_client, method) -> None:
    response = _send(admin_client, method, f"{URL}/bogus", {"content": "x"})

    assert response.status_code == 422


# --- records --------------------------------------------------------------------


def test_records_search(admin_client, invoice_code) -> None:
    found = admin_client.get(f"{URL}/outbound_invoice/records", {"q": invoice_code})

    assert found.status_code == 200
    assert [r["code"] for r in found.json()["data"]] == [invoice_code]
    assert "ACME" in found.json()["data"][0]["label"]
    nothing = admin_client.get(f"{URL}/outbound_invoice/records", {"q": "nope-nope"})
    assert nothing.json()["data"] == []


def test_records_without_query(admin_client, invoice_code) -> None:
    response = admin_client.get(f"{URL}/outbound_invoice/records")

    assert invoice_code in [r["code"] for r in response.json()["data"]]


# --- preview --------------------------------------------------------------------


def test_preview_of_saved_template(admin_client, invoice_code) -> None:
    response = _send(
        admin_client,
        "post",
        f"{URL}/outbound_invoice/preview",
        {"record_code": invoice_code},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["error"] is None
    assert invoice_code in data["html"]


def test_preview_renders_unsaved_draft(admin_client, invoice_code) -> None:
    response = _send(
        admin_client,
        "post",
        f"{URL}/outbound_invoice/preview",
        {"record_code": invoice_code, "content": "<b>{{ invoice.customer.name }}</b>"},
    )

    assert response.json()["data"] == {"html": "<b>ACME s.r.o.</b>", "error": None}
    assert not DocumentTemplate.objects.exists()


@pytest.mark.parametrize(
    "content, line",
    [("{{ unclosed", 1), ("a\nb\n{{ 1 / 0 }}", 3), ("{{ ''.__class__ }}", 1)],
)
def test_preview_reports_template_errors_as_data(
    admin_client, invoice_code, content, line
) -> None:
    response = _send(
        admin_client,
        "post",
        f"{URL}/outbound_invoice/preview",
        {"record_code": invoice_code, "content": content},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["html"] is None
    assert data["error"]["line"] == line
    assert data["error"]["message"]


def test_preview_of_missing_record_is_not_found(admin_client, db) -> None:
    response = _send(
        admin_client, "post", f"{URL}/outbound_invoice/preview", {"record_code": "NOPE"}
    )

    assert response.status_code == 404


def test_preview_requires_record_code(admin_client) -> None:
    assert _send(admin_client, "post", f"{URL}/offer/preview", {}).status_code == 422


# --- pdf --------------------------------------------------------------------------


def _skip_without_weasyprint() -> None:
    try:
        import weasyprint  # type: ignore  # noqa: F401
    except OSError as e:
        pytest.skip(f"weasyprint system libraries missing: {e}")


def test_pdf_export_of_draft(admin_client, invoice_code) -> None:
    _skip_without_weasyprint()

    response = _send(
        admin_client,
        "post",
        f"{URL}/outbound_invoice/pdf",
        {"record_code": invoice_code, "content": "<p>{{ invoice.code }}</p>"},
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert invoice_code in response["Content-Disposition"]
    assert response.content.startswith(b"%PDF")


def test_pdf_export_of_broken_draft_is_422(admin_client, invoice_code) -> None:
    response = _send(
        admin_client,
        "post",
        f"{URL}/outbound_invoice/pdf",
        {"record_code": invoice_code, "content": "{{ unclosed"},
    )

    assert response.status_code == 422
