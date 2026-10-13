from __future__ import annotations

from typing import cast

from django.contrib.auth.models import User
from django.http import HttpRequest
from ninja import Router

from apps.warehouse.core.auth import superuser_auth
from apps.warehouse.core.schemas.users import (
    DeleteUserResponse,
    GetUserResponse,
    GetUsersResponse,
    UserCreateSchema,
    UserUpdateSchema,
)
from apps.warehouse.core.services.users import user_orm_to_schema, users_service

# superusers only
routes = Router(tags=["users"], auth=superuser_auth)


@routes.get("", response={200: GetUsersResponse})
def get_users(request: HttpRequest, search_term: str | None = None):
    return GetUsersResponse(
        data=[user_orm_to_schema(user) for user in users_service.get_users(search_term)]
    )


@routes.post("", response={200: GetUserResponse})
def create_user(request: HttpRequest, body: UserCreateSchema):
    return GetUserResponse(data=users_service.create_user(body))


@routes.put("/{user_id}", response={200: GetUserResponse})
def update_user(request: HttpRequest, user_id: int, body: UserUpdateSchema):
    return GetUserResponse(
        data=users_service.update_user(cast(User, request.user), user_id, body)
    )


@routes.delete("/{user_id}", response={200: DeleteUserResponse})
def delete_user(request: HttpRequest, user_id: int):
    return DeleteUserResponse(
        data=users_service.delete_user(cast(User, request.user), user_id)
    )
