from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.warehouse.core.schemas.analytics import (
    RecentOrdersDailyPointSchema,
    RecentOrdersSchema,
)
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderState,
    OutboundOrder,
    OutboundOrderState,
)
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    InboundWarehouseOrderState,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderState,
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


def _daily_active_counts(
    queryset, start: date, end: date, closed_states: list
) -> list[RecentOrdersDailyPointSchema]:
    """Count active (non-closed) orders that existed on each day."""
    tz = timezone.get_current_timezone()

    result = []
    for offset in range((end - start).days + 1):
        current_date = start + timedelta(days=offset)
        day_end = timezone.make_aware(datetime.combine(current_date, time.max), tz)

        # Count orders that:
        # - were created before or during this day
        # - were NOT in a closed state during this day
        # (either never closed, or closed after this day ended)
        count = (
            queryset.filter(
                created__lte=day_end,
            )
            .exclude(Q(state__in=closed_states) & Q(changed__lte=day_end))
            .count()
        )

        result.append(
            RecentOrdersDailyPointSchema(
                date=current_date,
                value=count,
            )
        )

    return result


class AnalyticsService:
    @staticmethod
    def get_active_warehouse_orders(days: int) -> RecentOrdersSchema:
        days = max(1, days)
        tz = timezone.get_current_timezone()
        today = timezone.now().astimezone(tz).date()
        start = today - timedelta(days=days - 1)

        inbound_qs = InboundWarehouseOrder.objects.all()
        outbound_qs = OutboundWarehouseOrder.objects.all()

        inbound_closed_states = [
            InboundWarehouseOrderState.IN_TRANSIT,
            InboundWarehouseOrderState.COMPLETED,
            InboundWarehouseOrderState.CANCELLED,
        ]
        outbound_closed_states = [
            OutboundWarehouseOrderState.COMPLETED,
            OutboundWarehouseOrderState.CANCELLED,
        ]

        return RecentOrdersSchema(
            days=days,
            inbound=_daily_active_counts(
                inbound_qs, start, today, inbound_closed_states
            ),
            outbound=_daily_active_counts(
                outbound_qs, start, today, outbound_closed_states
            ),
        )

    @staticmethod
    def get_active_orders(days: int) -> RecentOrdersSchema:
        days = max(1, days)
        tz = timezone.get_current_timezone()
        today = timezone.now().astimezone(tz).date()
        start = today - timedelta(days=days - 1)

        inbound_qs = InboundOrder.objects.all()
        outbound_qs = OutboundOrder.objects.all()

        inbound_closed_states = [
            InboundOrderState.DRAFT,
            InboundOrderState.COMPLETED,
            InboundOrderState.CANCELLED,
        ]
        outbound_closed_states = [
            OutboundOrderState.DRAFT,
            OutboundOrderState.COMPLETED,
            OutboundOrderState.CANCELLED,
            OutboundOrderState.COMPLETED_PAID,
            OutboundOrderState.SENT,
            OutboundOrderState.INVOICED,
            OutboundOrderState.WAITING_FOR_PAYMENT,
        ]

        return RecentOrdersSchema(
            days=days,
            inbound=_daily_active_counts(
                inbound_qs, start, today, inbound_closed_states
            ),
            outbound=_daily_active_counts(
                outbound_qs, start, today, outbound_closed_states
            ),
        )


analytics_service = AnalyticsService()
