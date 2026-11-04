from datetime import UTC, date, datetime

import pytest

from apps.warehouse.core.services.snapshot_schedules import is_last_day_of_month
from apps.warehouse.models.warehouse import (
    InventorySnapshot,
    InventorySnapshotTriggerSource,
)
from apps.warehouse.tasks import create_scheduled_inventory_snapshot


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 1, 31), True),
        (date(2026, 1, 30), False),
        (date(2026, 2, 28), True),
        (date(2026, 2, 27), False),
        (date(2028, 2, 28), False),  # leap year
        (date(2028, 2, 29), True),
        (date(2026, 4, 30), True),
        (date(2026, 4, 28), False),
        (date(2026, 12, 31), True),
    ],
)
def test_is_last_day_of_month(day, expected) -> None:
    assert is_last_day_of_month(day) is expected


def test_task_creates_scheduled_snapshot(db) -> None:
    snapshot_id = create_scheduled_inventory_snapshot()

    snapshot = InventorySnapshot.objects.get(pk=snapshot_id)
    assert snapshot.trigger_source == InventorySnapshotTriggerSource.SCHEDULED


def test_task_allows_several_runs_a_day(db) -> None:
    first = create_scheduled_inventory_snapshot()
    second = create_scheduled_inventory_snapshot()

    assert first != second
    assert InventorySnapshot.objects.count() == 2


@pytest.mark.parametrize(
    ("today", "created"),
    [(date(2026, 4, 30), 1), (date(2026, 4, 29), 0), (date(2026, 2, 28), 1)],
)
def test_last_day_only_skips_other_days(db, monkeypatch, today, created) -> None:
    monkeypatch.setattr("apps.warehouse.tasks.timezone.localdate", lambda: today)

    result = create_scheduled_inventory_snapshot(last_day_only=True)

    assert (result is not None) == bool(created)
    assert InventorySnapshot.objects.count() == created


@pytest.mark.parametrize(
    ("utc_now", "created"),
    [
        # 00:30 on 1 May in Prague - the last day of April is already over
        (datetime(2026, 4, 30, 22, 30, tzinfo=UTC), 0),
        # 01:30 on 30 April in Prague - last day, although it is still 29 April in UTC
        (datetime(2026, 4, 29, 23, 30, tzinfo=UTC), 1),
        # 23:30 on 30 April in Prague (21:30 UTC)
        (datetime(2026, 4, 30, 21, 30, tzinfo=UTC), 1),
        # 00:30 on 1 April in Prague, while UTC still says 31 March (a last day)
        (datetime(2026, 3, 31, 22, 30, tzinfo=UTC), 0),
    ],
)
def test_last_day_respects_django_timezone(db, settings, monkeypatch, utc_now, created):
    settings.TIME_ZONE = "Europe/Prague"
    monkeypatch.setattr("django.utils.timezone.now", lambda: utc_now)

    create_scheduled_inventory_snapshot(last_day_only=True)

    assert InventorySnapshot.objects.count() == created
