from __future__ import annotations

from typing import Annotated, Literal

from ninja import Schema
from pydantic import StringConstraints

from .base import Response

NormTypeLiteral = Literal["ISO", "CSN", "DIN", "EN"]


class NormRefSchema(Schema):
    """A norm without its aliases (what the aliases of a norm are made of)"""

    id: int
    code: str
    type: NormTypeLiteral
    label: str


class NormSchema(NormRefSchema):
    equivalents: list[NormRefSchema]


class NormCreateOrUpdateSchema(Schema):
    code: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
    ]
    type: NormTypeLiteral
    equivalent_ids: list[int] = []


class GetNormResponse(Response[NormSchema]): ...


class GetNormsResponse(Response[list[NormSchema]]): ...


class DeleteNormResponse(Response[None]): ...


class NormBackfillIssueSchema(Schema):
    product_code: str
    key: str
    value: str
    reason: str


class NormBackfillResultSchema(Schema):
    products_scanned: int
    customs_filled: int
    norms_linked: int
    norms_created: int
    aliases_linked: int
    # products whose norm was already set (kept untouched)
    norms_kept: int
    # still missing after the run
    without_customs: int
    without_norm: int
    invalid_count: int
    # capped, `invalid_count` holds the real number
    invalid: list[NormBackfillIssueSchema]


class NormBackfillJobStartedSchema(Schema):
    job_id: str


class NormBackfillJobStartedResponse(Response[NormBackfillJobStartedSchema]): ...


class NormBackfillJobStatusSchema(Schema):
    job_id: str
    state: Literal["pending", "running", "succeeded", "failed"]
    phase: str | None = None
    stage_done: int = 0
    stage_total: int = 0
    percent: float = 0
    result: NormBackfillResultSchema | None = None
    error: str | None = None


class NormBackfillJobStatusResponse(Response[NormBackfillJobStatusSchema]): ...
