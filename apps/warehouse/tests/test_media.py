from typing import cast

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.warehouse.tests.factories.user import UserFactory


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.DEBUG = False
    settings.MEDIA_ROOT = tmp_path
    for folder in ("avatars/1", "invoices/INV-1"):
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / "avatars/1/a.webp").write_bytes(b"img")
    (tmp_path / "invoices/INV-1/doc.pdf").write_bytes(b"pdf")
    return tmp_path


def test_avatar_is_public_without_debug(db) -> None:
    response = Client().get("/media/avatars/1/a.webp")

    assert response.status_code == 200


def test_invoice_requires_login(db) -> None:
    assert Client().get("/media/invoices/INV-1/doc.pdf").status_code == 404


def test_invoice_served_to_logged_in_user(db) -> None:
    client = Client()
    client.force_login(cast(User, UserFactory()))

    response = client.get("/media/invoices/INV-1/doc.pdf")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "path",
    ["avatars/1/missing.webp", "avatars/../invoices/INV-1/doc.pdf", "../etc/passwd"],
)
def test_missing_or_traversal_is_404(db, path) -> None:
    assert Client().get(f"/media/{path}").status_code == 404
