from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from apps.warehouse.core.schemas.settings import (
    GetGlobalSettingsResponse,
    GlobalSettingsUpdateSchema,
)
from apps.warehouse.core.services.settings import settings_service
from apps.warehouse.core.transformation import global_settings_orm_to_schema

routes = Router(tags=["settings"])


@routes.get("", response={200: GetGlobalSettingsResponse})
def get_global_settings(request: HttpRequest):
    return GetGlobalSettingsResponse(
        data=global_settings_orm_to_schema(settings_service.get_settings())
    )


@routes.put("", response={200: GetGlobalSettingsResponse})
def update_global_settings(request: HttpRequest, body: GlobalSettingsUpdateSchema):
    return GetGlobalSettingsResponse(
        data=global_settings_orm_to_schema(settings_service.update_settings(body))
    )
