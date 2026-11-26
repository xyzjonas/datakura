"""API facing part of the asynchronous norm backfill: start a job, read its state"""

import uuid

from celery.result import AsyncResult
from loguru import logger

from apps.warehouse.core.exceptions import NotFoundException
from apps.warehouse.core.schemas.norm import (
    NormBackfillJobStartedSchema,
    NormBackfillJobStatusSchema,
    NormBackfillResultSchema,
)
from apps.warehouse.tasks import PROGRESS_STATE, run_norm_backfill

_RUNNING_STATES = {"STARTED", "RETRY", PROGRESS_STATE}
_PROGRESS_FIELDS = ("phase", "stage_done", "stage_total", "percent")


class NormBackfillJobService:
    def start(self) -> NormBackfillJobStartedSchema:
        job_id = str(uuid.uuid4())
        run_norm_backfill.apply_async(task_id=job_id)
        logger.info("Norm backfill job {} queued", job_id)
        return NormBackfillJobStartedSchema(job_id=job_id)

    def get_status(self, job_id: str) -> NormBackfillJobStatusSchema:
        try:
            job_id = str(uuid.UUID(job_id))
        except ValueError:
            raise NotFoundException(f"Norm job '{job_id}' not found") from None

        task = AsyncResult(job_id)
        state = task.state
        if state in _RUNNING_STATES:
            info = task.info if isinstance(task.info, dict) else {}
            meta = {k: info[k] for k in _PROGRESS_FIELDS if k in info}
            return NormBackfillJobStatusSchema(job_id=job_id, state="running", **meta)
        if state == "SUCCESS":
            return NormBackfillJobStatusSchema(
                job_id=job_id,
                state="succeeded",
                percent=100,
                phase="done",
                result=NormBackfillResultSchema(**task.result),
            )
        if state in ("FAILURE", "REVOKED"):
            logger.error("Norm backfill job {} crashed: {}", job_id, task.result)
            return NormBackfillJobStatusSchema(
                job_id=job_id,
                state="failed",
                error=f"Backfill interrupted: {task.result}",
            )
        # Celery reports unknown ids as PENDING, too
        return NormBackfillJobStatusSchema(job_id=job_id, state="pending")


norm_backfill_job_service = NormBackfillJobService()
