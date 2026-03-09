from __future__ import annotations

from datetime import datetime
from typing import Literal

from ninja import Schema
from pydantic import Field

from .base import BaseResponse


class AuditTimelineEntrySchema(Schema):
    id: int
    source: Literal["audit", "movement"]
    happened_at: datetime

    actor_user: str | None = None

    action: str | None = None
    reason: str | None = None
    changes: dict = Field(default_factory=dict)
    object_repr: str | None = None


class GetAuditTimelineResponse(BaseResponse):
    data: list[AuditTimelineEntrySchema]
