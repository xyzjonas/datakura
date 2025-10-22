from __future__ import annotations

from datetime import datetime
from typing import Any

from ninja import Schema
from pydantic import BaseModel


class BaseSchema(Schema):
    created: datetime
    changed: datetime


class BaseResponse(BaseModel):
    success: bool = True
    message: str | None = None
    data: Any
