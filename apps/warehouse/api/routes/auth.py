from typing import cast

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import User
from django.http import HttpRequest
from ninja import Router
from ninja import File
from ninja.files import UploadedFile
from ninja.responses import Status

from apps.warehouse.core.schemas.auth import (
    ChangePasswordResponse,
    LoginFormSchema,
    SigninResponse,
    SignoutResponse,
    WhoamiResponse,
    AuthData,
)
from apps.warehouse.core.schemas.printer import (
    SetDefaultPrinterRequestSchema,
    SetDefaultPrinterResponse,
)
from apps.warehouse.core.schemas.users import ChangePasswordSchema
from apps.warehouse.core.services.printers import printers_service
from apps.warehouse.core.services.users import users_service


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


def build_auth_data(request: HttpRequest, user: User) -> AuthData:
    return AuthData(
        username=user.username,
        user_id=user.id,
        group=get_user_group(user),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_superuser=user.is_superuser,
        avatar_url=users_service.get_avatar_url(user),
        last_login=user.last_login,
        date_joined=user.date_joined,
        expiry_date=request.session.get_expiry_date(),
        default_printer=printers_service.get_default_printer(user),
    )


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
            data=build_auth_data(request, cast(User, user)),
        )
    else:
        return 401, SigninResponse(success=False, message="Invalid credentials")


@routes.post("logout", response={200: SignoutResponse})
def logout_user(request: HttpRequest):
    logout(request)

    return SignoutResponse(
        success=True,
    )


@routes.get("whoami", response={200: WhoamiResponse, 401: SigninResponse})
def whoami(request: HttpRequest):
    if request.user.is_authenticated:
        return Status(
            200,
            WhoamiResponse(data=build_auth_data(request, cast(User, request.user))),
        )

    return 401, SigninResponse(success=False, message="Invalid credentials")


@routes.post("default-printer", response={200: SetDefaultPrinterResponse})
def set_default_printer(
    request: HttpRequest,
    body: SetDefaultPrinterRequestSchema,
):
    return SetDefaultPrinterResponse(
        data=printers_service.set_default_printer(
            cast(User, request.user), body.printer_code
        )
    )


@routes.post("change-password", response={200: ChangePasswordResponse})
def change_password(request: HttpRequest, body: ChangePasswordSchema):
    users_service.change_password(request, cast(User, request.user), body)
    return ChangePasswordResponse()


@routes.post("avatar", response={200: WhoamiResponse})
def upload_avatar(request: HttpRequest, avatar: File[UploadedFile]):
    user = cast(User, request.user)
    users_service.set_avatar(user, avatar)
    return WhoamiResponse(data=build_auth_data(request, user))


@routes.delete("avatar", response={200: WhoamiResponse})
def delete_avatar(request: HttpRequest):
    user = cast(User, request.user)
    users_service.remove_avatar(user)
    return WhoamiResponse(data=build_auth_data(request, user))
