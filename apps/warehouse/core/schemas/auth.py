from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .base import BaseResponse


class LoginFormSchema(BaseModel):
    username: str
    password: str


class AuthData(BaseModel):
    user_id: int
    username: str
    group: str | None = None
    active_site: str | None = None
    expiry_date: datetime


class SigninResponse(BaseResponse):
    success: bool
    message: str
    data: AuthData | None = None


class WhoamiResponse(BaseResponse):
    data: AuthData


class SignoutResponse(BaseResponse):
    data: None = None


class SwitchSiteBody(BaseModel):
    site_code: str | None
