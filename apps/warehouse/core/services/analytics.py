from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.warehouse.core.schemas.analytics import (
    RecentOrdersDailyPointSchema,
    RecentOrdersSchema,
)
from apps.warehouse.models.orders import InboundOrder, OutboundOrder
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    OutboundWarehouseOrder,
)


def _daily_counts(
    queryset, start: date, end: date
) -> list[RecentOrdersDailyPointSchema]:
    tz = timezone.get_current_timezone()
    raw = (
        queryset.annotate(day=TruncDate("created", tzinfo=tz))
        .values("day")
        .annotate(value=Count("id"))
    )
    counts: dict[date, int] = {row["day"]: row["value"] for row in raw}

    return [
        RecentOrdersDailyPointSchema(
            date=start + timedelta(days=offset),
            value=counts.get(start + timedelta(days=offset), 0),
        )
        for offset in range((end - start).days + 1)
    ]


class AnalyticsService:
    @staticmethod
    def get_recent_orders(days: int) -> RecentOrdersSchema:
        days = max(1, days)
        tz = timezone.get_current_timezone()
        today = timezone.now().astimezone(tz).date()
        start = today - timedelta(days=days - 1)
        window_start = timezone.make_aware(datetime.combine(start, time.min), tz)

        inbound_qs = InboundWarehouseOrder.objects.filter(created__gte=window_start)
        outbound_qs = OutboundWarehouseOrder.objects.filter(created__gte=window_start)

        return RecentOrdersSchema(
            days=days,
            inbound=_daily_counts(inbound_qs, start, today),
            outbound=_daily_counts(outbound_qs, start, today),
        )

    @staticmethod
    def get_recent_orders_activity(days: int) -> RecentOrdersSchema:
        days = max(1, days)
        tz = timezone.get_current_timezone()
        today = timezone.now().astimezone(tz).date()
        start = today - timedelta(days=days - 1)
        window_start = timezone.make_aware(datetime.combine(start, time.min), tz)

        inbound_qs = InboundOrder.objects.filter(created__gte=window_start)
        outbound_qs = OutboundOrder.objects.filter(created__gte=window_start)

        return RecentOrdersSchema(
            days=days,
            inbound=_daily_counts(inbound_qs, start, today),
            outbound=_daily_counts(outbound_qs, start, today),
        )


analytics_service = AnalyticsService()
