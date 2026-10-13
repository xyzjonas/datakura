from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .base import BaseResponse
from .printer import PrinterSchema


class LoginFormSchema(BaseModel):
    username: str
    password: str


class AuthData(BaseModel):
    user_id: int
    username: str
    group: str | None = None
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    is_superuser: bool = False
    avatar_url: str | None = None
    last_login: datetime | None = None
    date_joined: datetime | None = None
    expiry_date: datetime
    default_printer: PrinterSchema | None = None


class SigninResponse(BaseResponse):
    success: bool
    message: str
    data: AuthData | None = None


class WhoamiResponse(BaseResponse):
    data: AuthData


class SignoutResponse(BaseResponse):
    data: None = None


class ChangePasswordResponse(BaseResponse):
    data: None = None
