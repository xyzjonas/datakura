from dataclasses import asdict
from typing import Any

from celery import shared_task
from django.utils import timezone

from apps.warehouse.core.services.data_import.progress import ProgressSnapshot
from apps.warehouse.core.services.inventory_snapshots import inventory_snapshot_service
from apps.warehouse.core.services.snapshot_schedules import is_last_day_of_month
from apps.warehouse.models.warehouse import InventorySnapshotTriggerSource
from apps.warehouse.core.services.data_import.staged_import import (
    StagedWarehouse,
    run_staged_import,
)

PROGRESS_STATE = "PROGRESS"


@shared_task
def add(x: int, y: int) -> int:
    """Example task: proves the worker round-trip works."""
    return x + y


@shared_task(bind=True, name="data_import.run", time_limit=3 * 60 * 60)
def run_data_import(
    self,
    products: str | None,
    customers: str | None,
    warehouses: list[StagedWarehouse],
) -> dict[str, Any]:
    """
    Legacy data import on files staged by the API. The state is published through the
    task result backend (not the DB: the import transaction is invisible until commit).
    """

    def publish(snapshot: ProgressSnapshot) -> None:
        self.update_state(state=PROGRESS_STATE, meta=asdict(snapshot))

    return run_staged_import(products, customers, warehouses, sink=publish)


@shared_task(name="warehouse.create_scheduled_inventory_snapshot")
def create_scheduled_inventory_snapshot(last_day_only: bool = False) -> int | None:
    """
    Periodic task (django-celery-beat) capturing the inventory snapshot.

    `last_day_only` schedules fire on days 28-31 - the task is skipped (returns None)
    unless today really is the last day of the month.
    """
    today = timezone.localdate()
    if last_day_only and not is_last_day_of_month(today):
        return None

    # bucket_key only labels the run - without a cadence no deduplication applies, so
    # any number of schedules may legitimately fire on the same day.
    snapshot = inventory_snapshot_service.create_snapshot(
        trigger_source=InventorySnapshotTriggerSource.SCHEDULED,
        bucket_key=today.isoformat(),
    )
    return snapshot.id
