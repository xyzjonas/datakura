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
