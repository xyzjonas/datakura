from calendar import monthrange
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.warehouse.core.schemas.warehouse import (
    WarehouseOrderCreateSchema,
    WarehouseOrderSchema,
)
from apps.warehouse.core.transformation import (
    warehouse_inbound_order_orm_to_schema,
)
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderState,
)
from apps.warehouse.models.warehouse import WarehouseOrderIn


def _get_end_of_month(date: datetime) -> datetime:
    last_day = monthrange(date.year, date.month)[1]
    return date.replace(day=last_day)


def _get_month_range(date: datetime) -> tuple[datetime, datetime]:
    last_day = _get_end_of_month(date)
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0), last_day


class WarehouseService:
    @staticmethod
    def generate_next_inbound_order_code() -> str:
        now = timezone.now()
        dt_range = _get_month_range(now)
        orders_this_month = WarehouseOrderIn.objects.filter(
            created__range=dt_range
        ).count()
        return f"P{now.year}{now.month:02d}{orders_this_month + 1:04d}"

    @staticmethod
    def create_inbound_order(
        params: WarehouseOrderCreateSchema,
    ) -> WarehouseOrderSchema:
        code = WarehouseService.generate_next_inbound_order_code()
        purchase_order = InboundOrder.objects.get(code=params.purchase_order_code)
        with transaction.atomic():
            warehouse_order = WarehouseOrderIn.objects.create(
                code=code, order=purchase_order
            )
            purchase_order.state = InboundOrderState.PUTAWAY
            purchase_order.save()

        return warehouse_inbound_order_orm_to_schema(warehouse_order)


warehouse_service = WarehouseService()
