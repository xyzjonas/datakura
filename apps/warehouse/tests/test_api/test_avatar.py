from io import BytesIO
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from apps.warehouse.core.services import users as users_service_module

URL = "/api/v1/auth/avatar"
WHOAMI = "/api/v1/auth/whoami"


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def client(user) -> Client:
    client = Client()
    client.force_login(user)
    return client


def _image_file(
    size=(800, 400), mode="RGB", fmt="PNG", name="me.png"
) -> SimpleUploadedFile:
    buffer = BytesIO()
    color = (255, 0, 0, 0) if mode == "RGBA" else "red"  # transparent for RGBA
    Image.new(mode, size, color).save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{fmt}")


def _stored(media_root: Path) -> list[Path]:
    return [p for p in media_root.rglob("*") if p.is_file()]


def test_whoami_has_no_avatar_by_default(client) -> None:
    assert client.get(WHOAMI).json()["data"]["avatar_url"] is None


def test_upload_avatar_is_cropped_square_and_compressed(client, media_root) -> None:
    response = client.post(URL, {"avatar": _image_file()})

    assert response.status_code == 200
    url = response.json()["data"]["avatar_url"]
    assert url.startswith("/media/avatars/") and url.endswith(".webp")
    assert client.get(WHOAMI).json()["data"]["avatar_url"] == url
    (stored,) = _stored(media_root)
    with Image.open(stored) as img:
        assert img.format == "WEBP"
        assert img.size == (256, 256)


@pytest.mark.parametrize(
    "size, expected",
    [
        ((100, 60), (60, 60)),  # small: squared, never upscaled
        ((256, 256), (256, 256)),
        ((300, 1000), (256, 256)),  # portrait
    ],
)
def test_upload_avatar_sizes(client, media_root, size, expected) -> None:
    response = client.post(URL, {"avatar": _image_file(size=size)})

    assert response.status_code == 200
    with Image.open(_stored(media_root)[0]) as img:
        assert img.size == expected


def test_upload_avatar_keeps_transparency(client, media_root) -> None:
    client.post(URL, {"avatar": _image_file(mode="RGBA")})

    with Image.open(_stored(media_root)[0]) as img:
        assert "A" in img.getbands()


def test_replace_avatar_removes_old_file(client, media_root) -> None:
    first = client.post(URL, {"avatar": _image_file()}).json()["data"]["avatar_url"]
    second = client.post(URL, {"avatar": _image_file(fmt="JPEG", name="a.jpg")}).json()[
        "data"
    ]["avatar_url"]

    assert first != second
    assert len(_stored(media_root)) == 1


def test_delete_avatar(client, media_root) -> None:
    client.post(URL, {"avatar": _image_file()})

    response = client.delete(URL)

    assert response.status_code == 200
    assert response.json()["data"]["avatar_url"] is None
    assert _stored(media_root) == []


def test_delete_without_avatar_is_noop(client) -> None:
    assert client.delete(URL).status_code == 200


def test_not_an_image_rejected(client, media_root) -> None:
    fake = SimpleUploadedFile("x.png", b"definitely not an image")

    response = client.post(URL, {"avatar": fake})

    assert response.status_code == 400
    assert _stored(media_root) == []


def test_too_large_upload_rejected(client, monkeypatch) -> None:
    monkeypatch.setattr(users_service_module, "AVATAR_MAX_UPLOAD_BYTES", 10)

    assert client.post(URL, {"avatar": _image_file()}).status_code == 400


def test_too_many_pixels_rejected(client, monkeypatch) -> None:
    monkeypatch.setattr(users_service_module, "AVATAR_MAX_SOURCE_PIXELS", 100)

    assert client.post(URL, {"avatar": _image_file()}).status_code == 400


def test_missing_file_is_422(client) -> None:
    assert client.post(URL).status_code == 422


@pytest.mark.parametrize("method", ["post", "delete"])
def test_anonymous_gets_401(db, method) -> None:
    assert getattr(Client(), method)(URL).status_code == 401
