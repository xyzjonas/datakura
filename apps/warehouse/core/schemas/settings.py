from __future__ import annotations

from pydantic import Field

from ninja import Schema

from apps.warehouse.core.schemas.base import BaseResponse, BaseSchema


class GlobalSettingsSchema(BaseSchema):
    # 0 = no minimum
    minimum_item_value: float


class GlobalSettingsUpdateSchema(Schema):
    minimum_item_value: float = Field(ge=0)


class GetGlobalSettingsResponse(BaseResponse):
    data: GlobalSettingsSchema
