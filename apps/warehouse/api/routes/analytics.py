from datetime import datetime

from django.http import HttpRequest
from ninja import Router, Query
from ninja.pagination import paginate

from apps.warehouse.api.pagination import (
    InventorySnapshotsPagination,
    WarehouseMovementsPagination,
)
from apps.warehouse.core.schemas.analytics import (
    GetInventorySnapshotResponse,
    GetLatestInventoryValueResponse,
    GetRecentActivityResponse,
    GetRecentOrdersActivityResponse,
    GetRecentOrdersResponse,
    GetRecentWarehouseMovementsResponse,
    InventorySnapshotCreateSchema,
    InventorySnapshotSummarySchema,
    WarehouseMovementSchema,
)
from apps.warehouse.core.services.analytics import analytics_service
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.inventory_snapshots import inventory_snapshot_service
from apps.warehouse.core.services.movements import movement_service

routes = Router(tags=["analytics"])


@routes.get("/inventory-value", response={200: GetLatestInventoryValueResponse})
def get_inventory_value(request: HttpRequest):
    return GetLatestInventoryValueResponse(
        data=inventory_snapshot_service.get_latest_snapshot_value()
    )


@routes.get("/recent-activity", response={200: GetRecentActivityResponse})
def get_recent_activity(request: HttpRequest):
    return GetRecentActivityResponse(data=audit_service.get_recent_activity(limit=8))


@routes.get("/recent-orders", response={200: GetRecentOrdersResponse})
def get_recent_orders(request: HttpRequest, days: int = 14):
    return GetRecentOrdersResponse(
        data=analytics_service.get_active_warehouse_orders(days=days)
    )


@routes.get("/recent-orders-activity", response={200: GetRecentOrdersActivityResponse})
def get_recent_orders_activity(request: HttpRequest, days: int = 14):
    return GetRecentOrdersActivityResponse(
        data=analytics_service.get_active_orders(days=days)
    )


@routes.get(
    "/inventory-snapshots", response={200: list[InventorySnapshotSummarySchema]}
)
@paginate(InventorySnapshotsPagination)
def get_inventory_snapshots(request: HttpRequest):
    return inventory_snapshot_service.list_snapshots_queryset()


@routes.post("/inventory-snapshots", response={200: GetInventorySnapshotResponse})
def create_inventory_snapshot(
    request: HttpRequest,
    body: InventorySnapshotCreateSchema,
):
    snapshot = inventory_snapshot_service.create_snapshot(
        cadence=body.cadence,
        force=body.force,
    )
    return GetInventorySnapshotResponse(data=snapshot)


@routes.get(
    "/inventory-snapshots/{snapshot_id}",
    response={200: GetInventorySnapshotResponse},
)
def get_inventory_snapshot(request: HttpRequest, snapshot_id: int):
    return GetInventorySnapshotResponse(
        data=inventory_snapshot_service.get_snapshot(snapshot_id)
    )


@routes.get("/warehouse-movements", response={200: list[WarehouseMovementSchema]})
@paginate(WarehouseMovementsPagination)
def get_warehouse_movements(
    request: HttpRequest,
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    stock_product_id: int | None = Query(None),
    location_from_id: int | None = Query(None),
    location_to_id: int | None = Query(None),
    batch_id: int | None = Query(None),
    worker_id: int | None = Query(None),
):
    return movement_service.get_movements_queryset(
        from_date=from_date,
        to_date=to_date,
        stock_product_id=stock_product_id,
        location_from_id=location_from_id,
        location_to_id=location_to_id,
        batch_id=batch_id,
        worker_id=worker_id,
    )


@routes.get(
    "/recent-warehouse-movements", response={200: GetRecentWarehouseMovementsResponse}
)
def get_recent_warehouse_movements(request: HttpRequest):
    return GetRecentWarehouseMovementsResponse(
        data=movement_service.get_recent_movements(limit=8)
    )
