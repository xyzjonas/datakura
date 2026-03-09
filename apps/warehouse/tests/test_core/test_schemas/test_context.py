from types import SimpleNamespace

from apps.warehouse.core.schemas.context import RequestContext


def test_from_django_request_accepts_typed_user_values() -> None:
    req = SimpleNamespace(user=SimpleNamespace(id=7, username="john"))

    context = RequestContext.from_django_request(req)  # type: ignore

    assert context.user_id == 7
    assert context.username == "john"
