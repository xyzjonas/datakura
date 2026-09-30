from __future__ import annotations

from typing import Literal

from ninja import Schema

from .base import Response


class ProductImportResultSchema(Schema):
    created: int
    updated: int
    skipped: int
    barcodes_attached: int
    warnings: list[str]


class CustomerImportResultSchema(Schema):
    created: int
    updated: int
    contacts: int
    groups_created: int
    warnings: list[str]


class WarehouseImportResultSchema(Schema):
    warehouse: str
    warehouse_created: bool
    locations_created: int
    locations_existing: int
    items_created: int


class DataImportResultSchema(Schema):
    products: ProductImportResultSchema | None = None
    customers: CustomerImportResultSchema | None = None
    warehouses: list[WarehouseImportResultSchema]


class DataImportResponse(Response[DataImportResultSchema]): ...


class DataImportJobStartedSchema(Schema):
    job_id: str


class DataImportJobStartedResponse(Response[DataImportJobStartedSchema]): ...


class DataImportJobStatusSchema(Schema):
    job_id: str
    state: Literal["pending", "running", "succeeded", "failed"]
    stage: str | None = None
    phase: str | None = None
    stage_done: int = 0
    stage_total: int = 0
    percent: float = 0
    result: DataImportResultSchema | None = None
    error: str | None = None


class DataImportJobStatusResponse(Response[DataImportJobStatusSchema]): ...
