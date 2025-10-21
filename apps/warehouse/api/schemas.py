from typing import Any

from pydantic import BaseModel


class BaseResponse(BaseModel):
    success: bool = True
    message: str | None = None
    data: Any


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
