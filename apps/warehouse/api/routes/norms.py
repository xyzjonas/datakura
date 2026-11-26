from __future__ import annotations

from django.http import HttpRequest
from ninja import Router, Status

from apps.warehouse.core.schemas.norm import (
    DeleteNormResponse,
    GetNormResponse,
    GetNormsResponse,
    NormBackfillJobStartedResponse,
    NormBackfillJobStatusResponse,
    NormCreateOrUpdateSchema,
)
from apps.warehouse.core.services.norm_backfill_jobs import norm_backfill_job_service
from apps.warehouse.core.services.norms import norms_service
from apps.warehouse.core.transformation import norm_orm_to_schema

routes = Router(tags=["norms"])

MAX_LISTED_NORMS = 100


@routes.get("", response={200: GetNormsResponse})
def get_norms(
    request: HttpRequest, search_term: str | None = None, type: str | None = None
):
    """Catalogue of norms for pickers - best `MAX_LISTED_NORMS` matches"""
    qs = norms_service.list_norms(search_term, type)[:MAX_LISTED_NORMS]
    return GetNormsResponse(data=[norm_orm_to_schema(n) for n in qs])


@routes.post("", response={200: GetNormResponse})
def create_norm(request: HttpRequest, body: NormCreateOrUpdateSchema):
    return GetNormResponse(data=norm_orm_to_schema(norms_service.create(body)))


@routes.post("/backfill", response={202: NormBackfillJobStartedResponse})
def start_norm_backfill(request: HttpRequest):
    """
    Queues the backfill of product norms and customs nomenclature from the legacy
    product metas. Poll `GET /backfill/jobs/{job_id}` for progress and the report.
    """
    return Status(
        202, NormBackfillJobStartedResponse(data=norm_backfill_job_service.start())
    )


@routes.get("/backfill/jobs/{job_id}", response={200: NormBackfillJobStatusResponse})
def get_norm_backfill_job(request: HttpRequest, job_id: str):
    return NormBackfillJobStatusResponse(
        data=norm_backfill_job_service.get_status(job_id)
    )


@routes.get("/{norm_id}", response={200: GetNormResponse})
def get_norm(request: HttpRequest, norm_id: int):
    return GetNormResponse(data=norm_orm_to_schema(norms_service.get(norm_id)))


@routes.put("/{norm_id}", response={200: GetNormResponse})
def update_norm(request: HttpRequest, norm_id: int, body: NormCreateOrUpdateSchema):
    return GetNormResponse(data=norm_orm_to_schema(norms_service.update(norm_id, body)))


@routes.delete("/{norm_id}", response={200: DeleteNormResponse})
def delete_norm(request: HttpRequest, norm_id: int):
    norms_service.delete(norm_id)
    return DeleteNormResponse(data=None)
