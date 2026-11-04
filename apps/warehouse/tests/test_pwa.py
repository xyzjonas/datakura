import pytest
from django.test import Client


@pytest.fixture(autouse=True)
def pwa_root(settings, tmp_path):
    settings.DEBUG = False
    settings.PWA_ROOT = tmp_path
    # rendering the Vue shell must not depend on a collectstatic'd frontend build
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
    for name in (
        "sw.js",
        "workbox-6b8d0bbe.js",
        "manifest.webmanifest",
        "favicon.ico",
        "logo.svg",
        "pwa-192x192.png",
        "maskable-icon-512x512.png",
        "apple-touch-icon-180x180.png",
        "secret.txt",
    ):
        (tmp_path / name).write_bytes(b"content")
    return tmp_path


@pytest.mark.parametrize(
    "filename",
    [
        "sw.js",
        "workbox-6b8d0bbe.js",
        "manifest.webmanifest",
        "favicon.ico",
        "logo.svg",
        "pwa-192x192.png",
        "maskable-icon-512x512.png",
        "apple-touch-icon-180x180.png",
    ],
)
def test_pwa_files_served_from_root_without_login(db, filename) -> None:
    response = Client().get(f"/{filename}")

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"content"  # type: ignore[attr-defined]


@pytest.mark.parametrize("filename", ["sw.js", "manifest.webmanifest"])
def test_sw_and_manifest_always_revalidated(db, filename) -> None:
    assert Client().get(f"/{filename}")["Cache-Control"] == "no-cache"


@pytest.mark.parametrize(
    "path",
    [
        "/secret.txt",  # exists in the dist dir but is not on the allowlist
        "/pwa-1x1.jpg",
        "/xsw.js",
        "/sw.js.map",
        "/orders",
        "/pwa-192x192.png/extra",
    ],
)
def test_other_paths_fall_through_to_vue_app(db, path) -> None:
    response = Client().get(path)

    assert response.status_code == 200
    assert response.templates[0].name == "index.html"  # type: ignore[attr-defined]


def test_missing_pwa_file_is_404(db, pwa_root) -> None:
    (pwa_root / "sw.js").unlink()

    assert Client().get("/sw.js").status_code == 404


def test_vue_shell_links_manifest(db) -> None:
    html = Client().get("/").content.decode()

    assert 'rel="manifest" href="/manifest.webmanifest"' in html
