from dataclasses import asdict
from typing import Any

from celery import shared_task

from apps.warehouse.core.services.data_import.progress import ProgressSnapshot
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
