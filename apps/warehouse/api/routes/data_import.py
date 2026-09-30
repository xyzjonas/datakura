from __future__ import annotations

from django.http import HttpRequest
from ninja import File, Form, Router, Status
from ninja.files import UploadedFile

from apps.warehouse.core.schemas.data_import import (
    DataImportJobStartedResponse,
    DataImportJobStatusResponse,
)
from apps.warehouse.core.services.data_import.jobs import DataImportJobService

routes = Router(tags=["data-import"])


@routes.post("", response={202: DataImportJobStartedResponse})
def start_data_import(
    request: HttpRequest,
    warehouse_ids: list[str] = Form([]),
    products_file: UploadedFile | None = File(None),
    customers_file: UploadedFile | None = File(None),
    warehouse_files: list[UploadedFile] = File([]),
):
    """
    Queues the legacy data import (products -> customers -> warehouse stock), which
    is all or nothing. Poll `GET /jobs/{job_id}` for the progress and the result.

    `warehouse_ids[i]` is the target warehouse name of `warehouse_files[i]`.
    """
    return Status(
        202,
        DataImportJobStartedResponse(
            data=DataImportJobService().start(
                products=products_file,
                customers=customers_file,
                warehouse_ids=warehouse_ids,
                warehouse_files=warehouse_files,
            )
        ),
    )


@routes.get("/jobs/{job_id}", response={200: DataImportJobStatusResponse})
def get_data_import_job(request: HttpRequest, job_id: str):
    return DataImportJobStatusResponse(data=DataImportJobService().get_status(job_id))
