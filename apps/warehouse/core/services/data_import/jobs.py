"""API facing part of the asynchronous import: start a job, read its state"""

import uuid
from collections.abc import Sequence

from celery.result import AsyncResult
from django.core.files.uploadedfile import UploadedFile
from loguru import logger

from apps.warehouse.core.exceptions import DataImportFailedError, NotFoundException
from apps.warehouse.core.schemas.data_import import (
    DataImportJobStartedSchema,
    DataImportJobStatusSchema,
    DataImportResultSchema,
)
from apps.warehouse.core.services.data_import.staged_import import (
    STATUS_FAILED,
    STATUS_SUCCEEDED,
    StagedWarehouse,
)
from apps.warehouse.core.services.data_import.staging import (
    discard_staged,
    stage_upload,
)
from apps.warehouse.core.services.data_import.stock_import import StockImportService
from apps.warehouse.tasks import PROGRESS_STATE, run_data_import

_RUNNING_STATES = {"STARTED", "RETRY", PROGRESS_STATE}


class DataImportJobService:
    def start(
        self,
        products: UploadedFile | None,
        customers: UploadedFile | None,
        warehouse_ids: Sequence[str],
        warehouse_files: Sequence[UploadedFile],
    ) -> DataImportJobStartedSchema:
        self._validate(products, customers, warehouse_ids, warehouse_files)

        job_id = str(uuid.uuid4())
        staged: list[str] = []
        try:
            products_path = self._stage(staged, job_id, "products", products)
            customers_path = self._stage(staged, job_id, "customers", customers)
            warehouses: list[StagedWarehouse] = [
                {
                    "warehouse": name,
                    "path": self._stage(staged, job_id, f"warehouse-{i}", file) or "",
                }
                for i, (name, file) in enumerate(zip(warehouse_ids, warehouse_files))
            ]
            run_data_import.apply_async(
                args=[products_path, customers_path, warehouses], task_id=job_id
            )
        except Exception:
            discard_staged(staged)
            raise

        logger.info("Data import job {} queued: {} files staged", job_id, len(staged))
        return DataImportJobStartedSchema(job_id=job_id)

    def get_status(self, job_id: str) -> DataImportJobStatusSchema:
        try:
            job_id = str(uuid.UUID(job_id))
        except ValueError:
            raise NotFoundException(f"Import job '{job_id}' not found") from None

        task = AsyncResult(job_id)
        state = task.state
        if state in _RUNNING_STATES:
            meta = task.info if isinstance(task.info, dict) else {}
            return DataImportJobStatusSchema(job_id=job_id, state="running", **meta)
        if state == "SUCCESS":
            return self._finished(job_id, task.result)
        if state in ("FAILURE", "REVOKED"):
            logger.error("Data import job {} crashed: {}", job_id, task.result)
            return DataImportJobStatusSchema(
                job_id=job_id,
                state="failed",
                error=f"Import interrupted: {task.result}",
            )
        # Celery reports unknown ids as PENDING, too
        return DataImportJobStatusSchema(job_id=job_id, state="pending")

    @staticmethod
    def _finished(job_id: str, envelope: dict) -> DataImportJobStatusSchema:
        if envelope.get("status") == STATUS_SUCCEEDED:
            return DataImportJobStatusSchema(
                job_id=job_id,
                state="succeeded",
                percent=100,
                phase="done",
                result=DataImportResultSchema(**envelope["result"]),
            )
        assert envelope.get("status") == STATUS_FAILED
        return DataImportJobStatusSchema(
            job_id=job_id, state="failed", error=envelope["error"]
        )

    @staticmethod
    def _validate(
        products: UploadedFile | None,
        customers: UploadedFile | None,
        warehouse_ids: Sequence[str],
        warehouse_files: Sequence[UploadedFile],
    ) -> None:
        if len(warehouse_ids) != len(warehouse_files):
            raise DataImportFailedError(
                f"Got {len(warehouse_ids)} warehouse ids but "
                f"{len(warehouse_files)} warehouse files"
            )
        if not (products or customers or warehouse_files):
            raise DataImportFailedError("Nothing to import - no file was uploaded")
        for name in warehouse_ids:
            try:
                StockImportService(name)
            except Exception as exc:
                raise DataImportFailedError(f"warehouse '{name}': {exc}") from exc

    @staticmethod
    def _stage(
        staged: list[str], job_id: str, label: str, file: UploadedFile | None
    ) -> str | None:
        if file is None:
            return None
        path = stage_upload(job_id, label, file)
        staged.append(path)
        return path
