from __future__ import annotations

from datetime import datetime
from typing import Any

from ninja import Schema
from pydantic import BaseModel, field_serializer


class BaseSchema(Schema):
    created: datetime
    changed: datetime

    @field_serializer("created", "changed")
    def serialize_datetime(self, dt: datetime) -> datetime:
        # Remove microseconds
        return dt.replace(microsecond=0)


class BaseResponse(BaseModel):
    success: bool = True
    message: str | None = None
    data: Any
