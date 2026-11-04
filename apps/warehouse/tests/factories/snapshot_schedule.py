import json

import factory
from django_celery_beat.models import CrontabSchedule, PeriodicTask
from factory.django import DjangoModelFactory

from apps.warehouse.core.services.snapshot_schedules import SNAPSHOT_TASK_NAME


class CrontabScheduleFactory(DjangoModelFactory):
    class Meta:
        model = CrontabSchedule

    minute = "0"
    hour = "2"
    day_of_month = "1"
    month_of_year = "*"
    day_of_week = "*"


class SnapshotScheduleFactory(DjangoModelFactory[PeriodicTask]):
    class Meta:
        model = PeriodicTask

    name = factory.Sequence(lambda n: f"Stav skladu {n}")
    task = SNAPSHOT_TASK_NAME
    crontab = factory.SubFactory(CrontabScheduleFactory)
    kwargs = json.dumps({"last_day_only": False})
    enabled = True
