from __future__ import annotations

from pydantic import Field

from ninja import Schema

from apps.warehouse.core.schemas.base import BaseResponse, BaseSchema
from apps.warehouse.models.settings import CodeSequence


class GlobalSettingsSchema(BaseSchema):
    # 0 = no minimum
    minimum_item_value: float
    code_sequence: CodeSequence


class GlobalSettingsUpdateSchema(Schema):
    # every field is optional - None = keep the current value
    minimum_item_value: float | None = Field(default=None, ge=0)
    code_sequence: CodeSequence | None = None  # None = keep current


class GetGlobalSettingsResponse(BaseResponse):
    data: GlobalSettingsSchema
