from typing import cast

import pytest
from django.contrib.auth.models import User
from django.test import Client

from apps.warehouse.tests.factories.user import UserFactory

URL = "/api/v1/users"
PASSWORD = "Secret-pass-123"
NEW_PASSWORD = "Another-str0ng-pass!"


def make_user(**kwargs) -> User:
    return cast(User, UserFactory(**kwargs))


@pytest.fixture
def superuser(db) -> User:
    return make_user(superuser=True)


@pytest.fixture
def admin_client(superuser) -> Client:
    client = Client()
    client.force_login(superuser)
    return client


def _payload(**overrides) -> dict:
    body = {
        "username": "new_user",
        "password": NEW_PASSWORD,
        "email": "new@example.com",
        "first_name": "New",
        "last_name": "User",
        "is_active": True,
        "is_superuser": False,
    }
    body.update(overrides)
    return body


def _update_payload(user: User, **overrides) -> dict:
    body = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
    }
    body.update(overrides)
    return body


def _put(client: Client, user_id: int, body: dict):
    return client.put(f"{URL}/{user_id}", data=body, content_type="application/json")


def _post(client: Client, body: dict, url: str = URL):
    return client.post(url, data=body, content_type="application/json")


# --- permissions -------------------------------------------------------------


@pytest.mark.parametrize(
    "method, path",
    [("get", ""), ("post", ""), ("put", "/1"), ("delete", "/1")],
)
def test_anonymous_gets_401(db, method, path) -> None:
    response = getattr(Client(), method)(
        f"{URL}{path}", content_type="application/json"
    )

    assert response.status_code == 401


@pytest.mark.parametrize("is_staff", [False, True])
@pytest.mark.parametrize(
    "method, path",
    [("get", ""), ("post", ""), ("put", "/1"), ("delete", "/1")],
)
def test_non_superuser_gets_403(db, user, is_staff, method, path) -> None:
    user.is_staff = is_staff
    user.save()
    client = Client()
    client.force_login(user)

    response = getattr(client, method)(f"{URL}{path}", content_type="application/json")

    assert response.status_code == 403
    assert response.json()["success"] is False


# --- list --------------------------------------------------------------------


def test_list_users_with_search(admin_client) -> None:
    make_user(username="alice", email="alice@corp.com")
    make_user(username="bob", email="bob@corp.com")

    all_users = admin_client.get(URL).json()["data"]
    found = admin_client.get(f"{URL}?search_term=ALI").json()["data"]

    assert {u["username"] for u in all_users} >= {"alice", "bob"}
    assert [u["username"] for u in found] == ["alice"]
    assert "password" not in found[0]


# --- create ------------------------------------------------------------------


def test_create_user(admin_client) -> None:
    response = _post(admin_client, _payload())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "new_user"
    assert data["is_superuser"] is False
    user = User.objects.get(username="new_user")
    assert user.check_password(NEW_PASSWORD)
    assert user.is_staff is False


def test_create_superuser_sets_staff(admin_client) -> None:
    response = _post(admin_client, _payload(is_superuser=True))

    assert response.status_code == 200
    user = User.objects.get(username="new_user")
    assert user.is_superuser and user.is_staff


@pytest.mark.parametrize(
    "overrides",
    [
        {"username": ""},
        {"username": "   "},
        {"username": "taken"},
        {"username": "TAKEN"},  # case-insensitive duplicate
        {"password": "short"},
        {"password": "12345678901"},  # numeric only
        {"password": "password"},  # common
    ],
)
def test_create_user_invalid(admin_client, overrides) -> None:
    make_user(username="taken")

    response = _post(admin_client, _payload(**overrides))

    assert response.status_code == 400
    assert not User.objects.filter(username="new_user").exists()


def test_create_user_missing_password_is_422(admin_client) -> None:
    body = _payload()
    del body["password"]

    assert _post(admin_client, body).status_code == 422


# --- update ------------------------------------------------------------------


def test_update_user(admin_client) -> None:
    target = make_user(username="target")

    response = _put(
        admin_client,
        target.pk,
        _update_payload(
            target, username="renamed", is_superuser=True, email="x@example.com"
        ),
    )

    assert response.status_code == 200
    target.refresh_from_db()
    assert target.username == "renamed"
    assert target.email == "x@example.com"
    assert target.is_superuser and target.is_staff
    assert target.check_password(PASSWORD)  # untouched without password


def test_update_user_demote_clears_staff(admin_client) -> None:
    target = make_user(superuser=True)

    response = _put(
        admin_client, target.pk, _update_payload(target, is_superuser=False)
    )

    assert response.status_code == 200
    target.refresh_from_db()
    assert not target.is_superuser and not target.is_staff


def test_update_user_resets_password(admin_client) -> None:
    target = make_user()

    response = _put(
        admin_client, target.pk, _update_payload(target, password=NEW_PASSWORD)
    )

    assert response.status_code == 200
    target.refresh_from_db()
    assert target.check_password(NEW_PASSWORD)


def test_update_user_weak_password_rejected(admin_client) -> None:
    target = make_user()

    response = _put(admin_client, target.pk, _update_payload(target, password="abc"))

    assert response.status_code == 400
    target.refresh_from_db()
    assert target.check_password(PASSWORD)


def test_update_user_duplicate_username(admin_client) -> None:
    make_user(username="taken")
    target = make_user(username="target")

    response = _put(admin_client, target.pk, _update_payload(target, username="taken"))

    assert response.status_code == 400


def test_update_user_keeps_own_username(admin_client, superuser) -> None:
    response = _put(
        admin_client, superuser.pk, _update_payload(superuser, first_name="Z")
    )

    assert response.status_code == 200


@pytest.mark.parametrize("overrides", [{"is_superuser": False}, {"is_active": False}])
def test_cannot_demote_or_deactivate_self(admin_client, superuser, overrides) -> None:
    response = _put(admin_client, superuser.pk, _update_payload(superuser, **overrides))

    assert response.status_code == 400
    superuser.refresh_from_db()
    assert superuser.is_superuser and superuser.is_active


def test_update_unknown_user_404(admin_client) -> None:
    body = _update_payload(make_user())

    assert _put(admin_client, 999999, body).status_code == 404


# --- delete ------------------------------------------------------------------


def test_delete_user(admin_client) -> None:
    target = make_user()

    response = admin_client.delete(f"{URL}/{target.pk}")

    assert response.status_code == 200
    assert response.json()["data"]["username"] == target.username
    assert not User.objects.filter(pk=target.pk).exists()


def test_cannot_delete_self(admin_client, superuser) -> None:
    response = admin_client.delete(f"{URL}/{superuser.pk}")

    assert response.status_code == 400
    assert User.objects.filter(pk=superuser.pk).exists()


def test_delete_unknown_user_404(admin_client) -> None:
    assert admin_client.delete(f"{URL}/999999").status_code == 404


# --- own account ---------------------------------------------------------------


def test_whoami_exposes_account_info(db) -> None:
    user = make_user(superuser=True, email="me@example.com")
    client = Client()
    client.force_login(user)

    data = client.get("/api/v1/auth/whoami").json()["data"]

    assert data["email"] == "me@example.com"
    assert data["first_name"] == user.first_name
    assert data["is_superuser"] is True
    assert data["group"] == "superuser"
    assert data["date_joined"]


class TestChangePassword:
    url = "/api/v1/auth/change-password"

    @pytest.fixture
    def client(self, user) -> Client:
        client = Client()
        client.force_login(user)
        return client

    def test_success_keeps_session(self, client, user) -> None:
        response = _post(
            client,
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            self.url,
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)
        assert client.get("/api/v1/auth/whoami").status_code == 200

    @pytest.mark.parametrize(
        "current, new",
        [
            ("wrong-password", NEW_PASSWORD),  # wrong current
            (PASSWORD, PASSWORD),  # same as current
            (PASSWORD, "short"),  # too short
            (PASSWORD, "1234567890123"),  # numeric
        ],
    )
    def test_rejected(self, client, user, current, new) -> None:
        response = _post(
            client, {"current_password": current, "new_password": new}, self.url
        )

        assert response.status_code == 400
        user.refresh_from_db()
        assert user.check_password(PASSWORD)

    def test_anonymous_gets_401(self, db) -> None:
        response = _post(
            Client(),
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            self.url,
        )

        assert response.status_code == 401
