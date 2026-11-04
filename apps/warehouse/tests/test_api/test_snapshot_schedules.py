import json

import pytest
from django_celery_beat.models import PeriodicTask
from ninja.testing import TestClient

from apps.warehouse.core.exceptions import ApiBaseException, NotFoundException
from apps.warehouse.api.routes.snapshot_schedules import routes
from apps.warehouse.tests.factories.snapshot_schedule import SnapshotScheduleFactory


@pytest.fixture
def client() -> TestClient:
    return TestClient(routes)


def test_list_only_returns_snapshot_schedules(db, client) -> None:
    SnapshotScheduleFactory.create(name="B")
    SnapshotScheduleFactory.create(name="A")
    SnapshotScheduleFactory.create(name="other", task="data_import.run")

    res = client.get("/")

    assert res.status_code == 200
    assert [s["name"] for s in res.json()["data"]] == ["A", "B"]


def test_list_empty(db, client) -> None:
    assert client.get("/").json()["data"] == []


@pytest.mark.parametrize("day", [1, 15, 28, 31])
def test_create_day_of_month(db, client, day) -> None:
    res = client.post(
        "/",
        json={
            "name": "Monthly",
            "mode": "day_of_month",
            "day_of_month": day,
            "hour": 3,
            "minute": 30,
        },
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert (data["mode"], data["day_of_month"], data["hour"], data["minute"]) == (
        "day_of_month",
        day,
        3,
        30,
    )
    task = PeriodicTask.objects.get(pk=data["id"])
    assert task.crontab.day_of_month == str(day)
    assert json.loads(task.kwargs) == {"last_day_only": False}
    assert task.enabled is True


def test_create_last_day_of_month(db, client) -> None:
    res = client.post(
        "/",
        json={"name": "Last", "mode": "last_day_of_month", "day_of_month": 5},
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["mode"] == "last_day_of_month"
    assert data["day_of_month"] is None
    task = PeriodicTask.objects.get(pk=data["id"])
    assert task.crontab.day_of_month == "28,29,30,31"
    assert json.loads(task.kwargs) == {"last_day_only": True}


@pytest.mark.parametrize(
    "body",
    [
        {"name": "x", "mode": "day_of_month"},
        {"name": "x", "mode": "day_of_month", "day_of_month": 0},
        {"name": "x", "mode": "day_of_month", "day_of_month": 32},
        {"name": "x", "day_of_month": 1, "hour": 24},
        {"name": "x", "day_of_month": 1, "minute": 60},
        {"name": "", "day_of_month": 1},
        {"name": "x", "mode": "weekly", "day_of_month": 1},
    ],
)
def test_create_rejects_invalid_input(db, client, body) -> None:
    res = client.post("/", json=body)

    assert res.status_code == 422
    assert not PeriodicTask.objects.exists()


def test_create_duplicate_name(db, client) -> None:
    SnapshotScheduleFactory.create(name="Dup")

    with pytest.raises(ApiBaseException, match="already exists") as exc:
        client.post("/", json={"name": "Dup", "day_of_month": 1})

    assert exc.value.http_status == 400
    assert PeriodicTask.objects.count() == 1


def test_update_switches_mode_and_disables(db, client) -> None:
    schedule = SnapshotScheduleFactory.create(name="Old")

    res = client.put(
        f"/{schedule.pk}",
        json={
            "name": "New",
            "enabled": False,
            "mode": "last_day_of_month",
            "hour": 23,
            "minute": 59,
        },
    )

    assert res.status_code == 200
    schedule.refresh_from_db()
    assert schedule.name == "New"
    assert schedule.enabled is False
    assert schedule.crontab.day_of_month == "28,29,30,31"
    assert json.loads(schedule.kwargs) == {"last_day_only": True}
    assert (schedule.crontab.hour, schedule.crontab.minute) == ("23", "59")


def test_update_keeping_own_name_is_allowed(db, client) -> None:
    schedule = SnapshotScheduleFactory.create(name="Same")

    res = client.put(f"/{schedule.pk}", json={"name": "Same", "day_of_month": 10})

    assert res.status_code == 200
    assert res.json()["data"]["day_of_month"] == 10


def test_update_to_taken_name(db, client) -> None:
    SnapshotScheduleFactory.create(name="Taken")
    schedule = SnapshotScheduleFactory.create(name="Mine")

    with pytest.raises(ApiBaseException, match="already exists"):
        client.put(f"/{schedule.pk}", json={"name": "Taken", "day_of_month": 1})


def test_update_does_not_touch_other_tasks(db, client) -> None:
    other = SnapshotScheduleFactory.create(name="other", task="data_import.run")

    with pytest.raises(NotFoundException):
        client.put(f"/{other.pk}", json={"name": "hack", "day_of_month": 1})

    other.refresh_from_db()
    assert other.name == "other"


def test_delete(db, client) -> None:
    schedule = SnapshotScheduleFactory.create()

    res = client.delete(f"/{schedule.pk}")

    assert res.status_code == 200
    assert res.json()["data"]["id"] == schedule.pk
    assert not PeriodicTask.objects.filter(pk=schedule.pk).exists()


def test_delete_unknown_and_foreign_task(db, client) -> None:
    other = SnapshotScheduleFactory.create(name="other", task="data_import.run")

    with pytest.raises(NotFoundException):
        client.delete("/9999")
    with pytest.raises(NotFoundException):
        client.delete(f"/{other.pk}")
    assert PeriodicTask.objects.filter(pk=other.pk).exists()


@pytest.mark.parametrize("tz", ["UTC", "Europe/Prague", "America/New_York"])
def test_schedule_is_anchored_to_configured_timezone(db, client, settings, tz) -> None:
    settings.TIME_ZONE = tz

    res = client.post("/", json={"name": "Local", "day_of_month": 1, "hour": 6})

    task = PeriodicTask.objects.get(pk=res.json()["data"]["id"])
    assert str(task.crontab.timezone) == tz
    assert res.json()["data"]["hour"] == 6
