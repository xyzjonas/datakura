from typing import cast

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import User
from django.http import HttpRequest
from ninja import Router

from apps.warehouse.core.schemas.auth import (
    LoginFormSchema,
    SigninResponse,
    SignoutResponse,
    WhoamiResponse,
    AuthData,
    SwitchSiteBody,
)


routes = Router(tags=["auth"])


def get_user_group(user: AbstractBaseUser) -> str | None:
    group_name = None

    if getattr(user, "is_superuser", False):
        group_name = "superuser"
    elif getattr(user, "is_staff", False):
        group_name = "admin"
    else:
        if group := cast(User, user).groups.first():
            group_name = group.name

    return group_name


@routes.post("login", response={200: SigninResponse, 401: SigninResponse}, auth=None)
def login_user(request: HttpRequest, credentials: LoginFormSchema):
    user = authenticate(
        request, username=credentials.username, password=credentials.password
    )
    if user is not None:
        login(request, user)
        return SigninResponse(
            success=True,
            message="Login successful",
            data=AuthData(
                username=user.username,
                user_id=user.id,
                group=get_user_group(user),
            ),
        )
    else:
        return 401, SigninResponse(success=False, message="Invalid credentials")


@routes.post("logout", response={200: SignoutResponse}, auth=None)
def logout_user(request: HttpRequest):
    logout(request)

    return SignoutResponse(
        success=True,
    )


@routes.get("whoami", response={200: WhoamiResponse, 401: SigninResponse})
def whoami(request: HttpRequest):
    if request.user.is_authenticated:
        return 200, WhoamiResponse(
            data=AuthData(
                username=request.user.username,
                user_id=request.user.id,
                group=get_user_group(request.user),
                active_site=request.session.get("active_site"),
            )
        )

    return 401, SigninResponse(success=False, message="Invalid credentials")


@routes.put(
    "whoami/site", response={200: WhoamiResponse, 401: SigninResponse}, auth=None
)
def switch_site(request: HttpRequest, body: SwitchSiteBody):
    if request.user.is_authenticated:
        request.session["active_site"] = body.site_code
        return 200, WhoamiResponse(
            data=AuthData(
                username=request.user.username,
                user_id=request.user.id,
                group=get_user_group(request.user),
                active_site=request.session.get("active_site"),
            )
        )

    return 401, SigninResponse(success=False, message="Invalid credentials")
