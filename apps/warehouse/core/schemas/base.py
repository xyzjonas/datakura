from __future__ import annotations

from datetime import datetime
from typing import Any, Generic

from mypyc.ir.ops import TypeVar
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


class EmptyResponse(BaseResponse):
    data: None = None


T = TypeVar("T")


class PaginatedResponse(BaseResponse, Generic[T]):
    data: list[T]
    count: int
    next: int | None
    previous: int | None
