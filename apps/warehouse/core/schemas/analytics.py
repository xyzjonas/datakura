from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from apps.warehouse.core.schemas.base import BaseResponse, PaginatedResponse, Response


InventorySnapshotValuationMode = Literal["purchase", "receipt"]


class InventorySnapshotCurrencyTotal(BaseModel):
    currency: str
    value: Decimal


class InventorySnapshotSummarySchema(BaseModel):
    id: int
    created: datetime
    changed: datetime
    captured_at: datetime
    trigger_source: str
    cadence: str | None = None
    bucket_key: str | None = None
    line_count: int
    purchase_totals: list[InventorySnapshotCurrencyTotal]
    receipt_totals: list[InventorySnapshotCurrencyTotal]
    receipt_unpriced_line_count: int
    receipt_complete: bool


class InventorySnapshotLineSchema(BaseModel):
    id: int
    warehouse_item_id: int | None = None
    warehouse_item_id_at_snapshot: int
    product_code: str
    product_name: str
    location_code: str
    quantity: Decimal
    unit_of_measure: str
    tracking_level: str
    purchase_currency: str
    purchase_unit_price: Decimal
    purchase_line_value: Decimal
    receipt_currency: str | None = None
    receipt_unit_price: Decimal | None = None
    receipt_line_value: Decimal | None = None
    receipt_price_available: bool
    receipt_price_fallback_reason: str | None = None


class InventorySnapshotDetailSchema(InventorySnapshotSummarySchema):
    lines: list[InventorySnapshotLineSchema]


class InventorySnapshotCreateSchema(BaseModel):
    cadence: str | None = None
    force: bool = False


class LatestInventoryValueSchema(BaseModel):
    snapshot: InventorySnapshotSummarySchema | None = None


class RecentActivityEntrySchema(BaseModel):
    id: int
    happened_at: datetime
    message: str
    object_repr: str | None = None
    actor_user: str | None = None
    action: str | None = None


class GetInventorySnapshotResponse(Response[InventorySnapshotDetailSchema]):
    data: InventorySnapshotDetailSchema


class GetInventorySnapshotsResponse(PaginatedResponse[InventorySnapshotSummarySchema]):
    data: list[InventorySnapshotSummarySchema]


class GetLatestInventoryValueResponse(BaseResponse):
    data: LatestInventoryValueSchema


class GetRecentActivityResponse(BaseResponse):
    data: list[RecentActivityEntrySchema]


class RecentOrdersDailyPointSchema(BaseModel):
    date: date
    value: int


class RecentOrdersSchema(BaseModel):
    days: int
    inbound: list[RecentOrdersDailyPointSchema]
    outbound: list[RecentOrdersDailyPointSchema]


class GetRecentOrdersResponse(BaseResponse):
    data: RecentOrdersSchema


class GetRecentOrdersActivityResponse(BaseResponse):
    data: RecentOrdersSchema


class StockProductMinimalSchema(BaseModel):
    code: str
    name: str
    unit_of_measure: str


class PackageInfo(BaseModel):
    type: str


class WarehouseItemMinimalSchema(BaseModel):
    id: int
    tracking_level: str
    package: PackageInfo | None = None


class WarehouseMovementSchema(BaseModel):
    id: int
    moved_at: datetime
    location_from_code: str | None = None
    location_to_code: str | None = None
    inbound_order_code: str | None = None
    outbound_order_code: str | None = None
    stock_product_code: str
    stock_product_name: str
    stock_product: StockProductMinimalSchema
    amount: Decimal
    item_id: int | None = None
    item: WarehouseItemMinimalSchema | None = None
    batch_id: int | None = None
    batch_barcode: str | None = None
    worker_username: str | None = None


class GetWarehouseMovementsResponse(PaginatedResponse[WarehouseMovementSchema]):
    data: list[WarehouseMovementSchema]


class GetRecentWarehouseMovementsResponse(BaseResponse):
    data: list[WarehouseMovementSchema]
