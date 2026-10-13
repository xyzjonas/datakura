from __future__ import annotations

from datetime import datetime

from ninja import Schema

from .base import BaseResponse, Response


class UserSchema(Schema):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_superuser: bool
    last_login: datetime | None = None
    date_joined: datetime


class GetUsersResponse(BaseResponse):
    data: list[UserSchema]


class GetUserResponse(Response[UserSchema]): ...


class DeleteUserResponse(Response[UserSchema]): ...


class UserCreateSchema(Schema):
    username: str
    password: str
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    is_superuser: bool = False


class UserUpdateSchema(Schema):
    username: str
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    is_superuser: bool = False
    # set only to reset the user's password
    password: str | None = None


class ChangePasswordSchema(Schema):
    current_password: str
    new_password: str
