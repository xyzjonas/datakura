import pytest
from django.contrib.auth.models import User

from ninja.testing.client import NinjaClientBase

from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.tests.factories.user import UserFactory


@pytest.fixture(autouse=True)
def use_utc_timezone(settings):
    settings.USE_TZ = True
    settings.TIME_ZONE = "UTC"


@pytest.fixture
def user(db) -> User:
    return UserFactory()  # type: ignore


@pytest.fixture
def context(user) -> RequestContext:
    return RequestContext(
        username=user.username,
        user_id=user.pk,
    )


@pytest.fixture(autouse=True)
def inject_test_client_user(monkeypatch, user):
    original_build_request = NinjaClientBase._build_request

    def _build_request_with_user(self, method, path, data, request_params):
        request_params.setdefault("user", user)
        return original_build_request(self, method, path, data, request_params)

    monkeypatch.setattr(NinjaClientBase, "_build_request", _build_request_with_user)


@pytest.fixture
def celery_inline(settings, tmp_path, monkeypatch):
    """
    Runs Celery tasks inline with results kept in memory - never touches the real
    broker / Redis. Uploads staged for the worker land in tmp_path.

    Celery prefers the Django `CELERY_*` settings over `app.conf.update()`, hence
    the overrides go through the `settings` fixture.
    """
    from conf.celery import app

    settings.MEDIA_ROOT = tmp_path
    settings.CELERY_BROKER_URL = "memory://"
    settings.CELERY_RESULT_BACKEND = "cache+memory://"
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = False
    settings.CELERY_TASK_STORE_EAGER_RESULT = True

    # read once at task registration, so the setting alone is too late
    from apps.warehouse.tasks import run_data_import

    monkeypatch.setattr(run_data_import, "store_eager_result", True)

    def reset_backend():
        app._local.__dict__.pop("backend", None)

    reset_backend()
    yield app
    reset_backend()
