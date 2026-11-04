from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from ninja import Schema
from pydantic import Field, model_validator

from .base import BaseResponse, Response


class SnapshotScheduleMode(StrEnum):
    DAY_OF_MONTH = "day_of_month"
    LAST_DAY_OF_MONTH = "last_day_of_month"


class SnapshotScheduleSchema(Schema):
    id: int
    name: str
    enabled: bool
    mode: SnapshotScheduleMode
    day_of_month: int | None = None
    hour: int
    minute: int
    last_run_at: datetime | None = None
    total_run_count: int = 0


class SnapshotScheduleCreateOrUpdateSchema(Schema):
    name: str = Field(min_length=1, max_length=200)
    enabled: bool = True
    mode: SnapshotScheduleMode = SnapshotScheduleMode.DAY_OF_MONTH
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    hour: int = Field(default=0, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)

    @model_validator(mode="after")
    def _day_required_for_day_of_month(self):
        if self.mode == SnapshotScheduleMode.DAY_OF_MONTH and self.day_of_month is None:
            raise ValueError("day_of_month is required for mode 'day_of_month'")
        return self


class GetSnapshotSchedulesResponse(BaseResponse):
    data: list[SnapshotScheduleSchema]


class GetSnapshotScheduleResponse(Response[SnapshotScheduleSchema]): ...


class DeleteSnapshotScheduleResponse(Response[SnapshotScheduleSchema]): ...
