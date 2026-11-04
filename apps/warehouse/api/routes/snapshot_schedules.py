from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from apps.warehouse.core.schemas.snapshot_schedule import (
    DeleteSnapshotScheduleResponse,
    GetSnapshotScheduleResponse,
    GetSnapshotSchedulesResponse,
    SnapshotScheduleCreateOrUpdateSchema,
)
from apps.warehouse.core.services.snapshot_schedules import snapshot_schedules_service

routes = Router(tags=["snapshot-schedules"])


@routes.get("", response={200: GetSnapshotSchedulesResponse})
def get_snapshot_schedules(request: HttpRequest):
    return GetSnapshotSchedulesResponse(
        data=snapshot_schedules_service.list_schedules()
    )


@routes.post("", response={200: GetSnapshotScheduleResponse})
def create_snapshot_schedule(
    request: HttpRequest, body: SnapshotScheduleCreateOrUpdateSchema
):
    return GetSnapshotScheduleResponse(
        data=snapshot_schedules_service.create_schedule(body)
    )


@routes.put("/{schedule_id}", response={200: GetSnapshotScheduleResponse})
def update_snapshot_schedule(
    request: HttpRequest, schedule_id: int, body: SnapshotScheduleCreateOrUpdateSchema
):
    return GetSnapshotScheduleResponse(
        data=snapshot_schedules_service.update_schedule(schedule_id, body)
    )


@routes.delete("/{schedule_id}", response={200: DeleteSnapshotScheduleResponse})
def delete_snapshot_schedule(request: HttpRequest, schedule_id: int):
    return DeleteSnapshotScheduleResponse(
        data=snapshot_schedules_service.delete_schedule(schedule_id)
    )
