from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest
from ninja import Router

from apps.warehouse.core.schemas.auth import (
    LoginFormSchema,
    SigninResponse,
    SignoutResponse,
    WhoamiResponse,
    AuthData,
)


routes = Router(tags=["auth"])


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
def whoami(request):
    if request.user.is_authenticated:
        return 200, WhoamiResponse(
            data=AuthData(
                username=request.user.username,
                user_id=request.user.id,
            )
        )

    return 401, SigninResponse(success=False, message="Invalid credentials")
