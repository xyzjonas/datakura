from __future__ import annotations

import calendar
import json
from datetime import date

from django.conf import settings
from django.db import IntegrityError, transaction
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from apps.warehouse.core.exceptions import ApiBaseException, NotFoundException
from apps.warehouse.core.schemas.snapshot_schedule import (
    SnapshotScheduleCreateOrUpdateSchema,
    SnapshotScheduleMode,
    SnapshotScheduleSchema,
)

SNAPSHOT_TASK_NAME = "warehouse.create_scheduled_inventory_snapshot"
LAST_DAY_KWARG = "last_day_only"
# crontab has no "last day of month" - fire on every candidate day and let the task
# skip those that are not the actual last day (see `is_last_day_of_month`)
LAST_DAY_CANDIDATES = "28,29,30,31"


def is_last_day_of_month(day: date) -> bool:
    return day.day == calendar.monthrange(day.year, day.month)[1]


class SnapshotSchedulesService:
    @staticmethod
    def _queryset():
        return PeriodicTask.objects.filter(task=SNAPSHOT_TASK_NAME).select_related(
            "crontab"
        )

    @staticmethod
    def _to_schema(task: PeriodicTask) -> SnapshotScheduleSchema:
        crontab = task.crontab
        last_day = bool(json.loads(task.kwargs or "{}").get(LAST_DAY_KWARG))
        return SnapshotScheduleSchema(
            id=task.pk,
            name=task.name,
            enabled=task.enabled,
            mode=(
                SnapshotScheduleMode.LAST_DAY_OF_MONTH
                if last_day
                else SnapshotScheduleMode.DAY_OF_MONTH
            ),
            day_of_month=None
            if last_day or crontab is None
            else int(crontab.day_of_month),
            hour=int(crontab.hour) if crontab else 0,
            minute=int(crontab.minute) if crontab else 0,
            last_run_at=task.last_run_at,
            total_run_count=task.total_run_count,
        )

    @staticmethod
    def _crontab(params: SnapshotScheduleCreateOrUpdateSchema) -> CrontabSchedule:
        if params.mode == SnapshotScheduleMode.LAST_DAY_OF_MONTH:
            day_of_month = LAST_DAY_CANDIDATES
        else:
            day_of_month = str(params.day_of_month)
        crontab, _ = CrontabSchedule.objects.get_or_create(
            minute=str(params.minute),
            hour=str(params.hour),
            day_of_month=day_of_month,
            month_of_year="*",
            day_of_week="*",
            timezone=settings.TIME_ZONE,
        )
        return crontab

    @staticmethod
    def _kwargs(params: SnapshotScheduleCreateOrUpdateSchema) -> str:
        last_day = params.mode == SnapshotScheduleMode.LAST_DAY_OF_MONTH
        return json.dumps({LAST_DAY_KWARG: last_day})

    @classmethod
    def _get(cls, schedule_id: int) -> PeriodicTask:
        try:
            return cls._queryset().get(pk=schedule_id)
        except PeriodicTask.DoesNotExist:
            raise NotFoundException("Snapshot schedule not found") from None

    @staticmethod
    def _name_taken(name: str, exclude_id: int | None = None) -> bool:
        return PeriodicTask.objects.filter(name=name).exclude(pk=exclude_id).exists()

    @classmethod
    def list_schedules(cls) -> list[SnapshotScheduleSchema]:
        return [cls._to_schema(t) for t in cls._queryset().order_by("name")]

    @classmethod
    @transaction.atomic
    def create_schedule(
        cls, params: SnapshotScheduleCreateOrUpdateSchema
    ) -> SnapshotScheduleSchema:
        name = params.name.strip()
        if cls._name_taken(name):
            raise ApiBaseException("Schedule with this name already exists", 400)
        try:
            task = PeriodicTask.objects.create(
                name=name,
                task=SNAPSHOT_TASK_NAME,
                crontab=cls._crontab(params),
                kwargs=cls._kwargs(params),
                enabled=params.enabled,
            )
        except IntegrityError:
            raise ApiBaseException("Schedule with this name already exists", 400)
        return cls._to_schema(task)

    @classmethod
    @transaction.atomic
    def update_schedule(
        cls, schedule_id: int, params: SnapshotScheduleCreateOrUpdateSchema
    ) -> SnapshotScheduleSchema:
        task = cls._get(schedule_id)
        name = params.name.strip()
        if cls._name_taken(name, exclude_id=task.pk):
            raise ApiBaseException("Schedule with this name already exists", 400)
        task.name = name
        task.crontab = cls._crontab(params)
        task.kwargs = cls._kwargs(params)
        task.enabled = params.enabled
        task.save()
        return cls._to_schema(task)

    @classmethod
    @transaction.atomic
    def delete_schedule(cls, schedule_id: int) -> SnapshotScheduleSchema:
        task = cls._get(schedule_id)
        schema = cls._to_schema(task)
        task.delete()
        return schema


snapshot_schedules_service = SnapshotSchedulesService()
