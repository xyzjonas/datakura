from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import InventorySnapshotsPagination
from apps.warehouse.core.schemas.analytics import (
    GetInventorySnapshotResponse,
    GetLatestInventoryValueResponse,
    GetRecentActivityResponse,
    GetRecentOrdersActivityResponse,
    GetRecentOrdersResponse,
    InventorySnapshotCreateSchema,
    InventorySnapshotSummarySchema,
)
from apps.warehouse.core.services.analytics import analytics_service
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.inventory_snapshots import inventory_snapshot_service

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
    return GetRecentOrdersResponse(data=analytics_service.get_recent_orders(days=days))


@routes.get("/recent-orders-activity", response={200: GetRecentOrdersActivityResponse})
def get_recent_orders_activity(request: HttpRequest, days: int = 14):
    return GetRecentOrdersActivityResponse(
        data=analytics_service.get_recent_orders_activity(days=days)
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
