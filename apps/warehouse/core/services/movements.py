from __future__ import annotations

from datetime import datetime

from django.db.models import QuerySet

from apps.warehouse.core.schemas.analytics import (
    PackageInfo,
    StockProductMinimalSchema,
    WarehouseItemMinimalSchema,
    WarehouseMovementSchema,
)
from apps.warehouse.models.warehouse import WarehouseMovement


class MovementService:
    def get_movements_queryset(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        stock_product_id: int | None = None,
        location_from_id: int | None = None,
        location_to_id: int | None = None,
        batch_id: int | None = None,
        worker_id: int | None = None,
    ) -> QuerySet[WarehouseMovement]:
        queryset = WarehouseMovement.objects.select_related(
            "stock_product",
            "stock_product__unit_of_measure",
            "location_from",
            "location_to",
            "inbound_order_code",
            "outbound_order_code",
            "batch",
            "worker",
            "item",
            "item__package_type",
        ).order_by("-moved_at")

        if from_date:
            queryset = queryset.filter(moved_at__gte=from_date)

        if to_date:
            queryset = queryset.filter(moved_at__lte=to_date)

        if stock_product_id:
            queryset = queryset.filter(stock_product_id=stock_product_id)

        if location_from_id:
            queryset = queryset.filter(location_from_id=location_from_id)

        if location_to_id:
            queryset = queryset.filter(location_to_id=location_to_id)

        if batch_id:
            queryset = queryset.filter(batch_id=batch_id)

        if worker_id:
            queryset = queryset.filter(worker_id=worker_id)

        return queryset

    def get_recent_movements(self, limit: int = 8) -> list[WarehouseMovementSchema]:
        movements = self.get_movements_queryset()[:limit]
        return [self.movement_to_schema(movement) for movement in movements]

    def movement_to_schema(
        self, movement: WarehouseMovement
    ) -> WarehouseMovementSchema:
        batch_barcode = None
        if movement.batch:
            primary_barcode = movement.batch.get_primary_barcode()
            if primary_barcode:
                batch_barcode = primary_barcode.code

        stock_product = StockProductMinimalSchema(
            code=movement.stock_product.code,
            name=movement.stock_product.name,
            unit_of_measure=movement.stock_product.unit_of_measure.name,
        )

        item = None
        if movement.item:
            package_info = None
            if movement.item.package_type:
                package_info = PackageInfo(type=movement.item.package_type.name)

            item = WarehouseItemMinimalSchema(
                id=movement.item.pk,
                tracking_level=movement.item.tracking_level,
                package=package_info,
            )

        return WarehouseMovementSchema(
            id=movement.pk,
            moved_at=movement.moved_at,
            location_from_code=movement.location_from.code
            if movement.location_from
            else None,
            location_to_code=movement.location_to.code
            if movement.location_to
            else None,
            inbound_order_code=movement.inbound_order_code.code
            if movement.inbound_order_code
            else None,
            outbound_order_code=movement.outbound_order_code.code
            if movement.outbound_order_code
            else None,
            stock_product_code=movement.stock_product.code,
            stock_product_name=movement.stock_product.name,
            stock_product=stock_product,
            amount=movement.amount,
            item_id=movement.item_id,
            item=item,
            batch_id=movement.batch_id,
            batch_barcode=batch_barcode,
            worker_username=movement.worker.username if movement.worker else None,
        )


movement_service = MovementService()
