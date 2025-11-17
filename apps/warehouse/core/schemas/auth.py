from __future__ import annotations

from pydantic import BaseModel

from .base import BaseResponse


class LoginFormSchema(BaseModel):
    username: str
    password: str


class AuthData(BaseModel):
    user_id: int
    username: str


class SigninResponse(BaseResponse):
    success: bool
    message: str
    data: AuthData | None = None


class WhoamiResponse(BaseResponse):
    data: AuthData


class SignoutResponse(BaseResponse):
    data: None = None
