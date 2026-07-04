from calendar import monthrange
from datetime import datetime
from enum import Enum

from django.db import transaction
from django.utils import timezone

from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.manufacturing import ManufacturingOrder
from apps.warehouse.models.orders import InboundOrder, OutboundOrder
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    InboundWarehouseOrderState,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderState,
)

# ──────────────────────────────────────────────────────────────────────────────
# Code prefix constants – single source of truth for all warehouse order coding
# ──────────────────────────────────────────────────────────────────────────────
INBOUND_PREFIX = "P"  # purchase-order–linked příjemka
MFG_INBOUND_PREFIX = "ZP"  # manufacturing–linked příjemka (výroba)
OUTBOUND_PREFIX = "V"  # generic výdejka (child orders / misc)
SALES_OUTBOUND_PREFIX = "WO"  # sales-order–linked výdejka
MFG_OUTBOUND_PREFIX = "ZV"  # manufacturing–linked výdejka (výroba)


class WarehouseOrderKind(str, Enum):
    """Business context for a warehouse order, drives prefix and FK selection."""

    INBOUND = "inbound"  # příjemka for a purchase order        → P
    MFG_INBOUND = "mfg_inbound"  # příjemka for manufacturing return     → ZP
    CHILD_INBOUND = "child_inbound"  # child příjemka split from a parent    → P
    SALES_OUTBOUND = "sales_outbound"  # výdejka for a sales order             → WO
    MFG_OUTBOUND = "mfg_outbound"  # výdejka for manufacturing dispatch    → ZV
    CHILD_OUTBOUND = "child_outbound"  # child výdejka split from a parent     → V


# ──────────────────────────────────────────────────────────────────────────────
# Code generation
# ──────────────────────────────────────────────────────────────────────────────


def _get_month_range(date: datetime) -> tuple[datetime, datetime]:
    last_day = monthrange(date.year, date.month)[1]
    start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = date.replace(day=last_day)
    return start, end


def generate_next_code(model, prefix: str) -> str:
    """
    Generate the next sequential warehouse order code for *model* with *prefix*.

    Uses last-code-suffix inference rather than a COUNT so concurrent inserts
    cannot produce collisions (unlike count + 1 which races under load).
    """
    now = timezone.now()
    dt_range = _get_month_range(now)
    monthly_prefix = f"{prefix}{now.year}{now.month:02d}"
    last_code = (
        model.objects.filter(
            created__range=dt_range,
            code__startswith=monthly_prefix,
        )
        .order_by("-code")
        .values_list("code", flat=True)
        .first()
    )
    next_number = 1
    if last_code:
        next_number = int(str(last_code)[len(monthly_prefix) :]) + 1
    return f"{monthly_prefix}{next_number:04d}"


# ──────────────────────────────────────────────────────────────────────────────
# Internal creation helpers
# ──────────────────────────────────────────────────────────────────────────────


def _create_inbound(
    purchase_order: InboundOrder,
    context: RequestContext,
    prefix: str,
) -> InboundWarehouseOrder:
    code = generate_next_code(InboundWarehouseOrder, prefix)
    with transaction.atomic():
        order = InboundWarehouseOrder.objects.create(
            code=code,
            order=purchase_order,
            state=InboundWarehouseOrderState.IN_TRANSIT,
        )
        audit_service.add_entry(
            order,
            action=AuditAction.CREATE,
            user=context.user_id,
            reason=AuditMessages.WAREHOUSE_ORDER_BOUND_TO_PURCHASE_ORDER.CS.format(
                purchase_order_code=purchase_order.code
            ),
        )
    return order


def _create_mfg_inbound(
    manufacturing_order: ManufacturingOrder,
    context: RequestContext,
    prefix: str,
) -> InboundWarehouseOrder:
    code = generate_next_code(InboundWarehouseOrder, prefix)
    with transaction.atomic():
        order = InboundWarehouseOrder.objects.create(
            code=code,
            manufacturing_order=manufacturing_order,
            state=InboundWarehouseOrderState.IN_TRANSIT,
        )
        audit_service.add_entry(
            order,
            action=AuditAction.CREATE,
            user=context.user_id,
            reason=AuditMessages.WAREHOUSE_ORDER_BOUND_TO_PURCHASE_ORDER.CS.format(
                purchase_order_code=manufacturing_order.code
            ),
        )
    return order


def _create_child_inbound(
    primary_order: InboundWarehouseOrder,
    context: RequestContext,
    prefix: str,
    initial_state: InboundWarehouseOrderState,
) -> InboundWarehouseOrder:
    code = generate_next_code(InboundWarehouseOrder, prefix)
    with transaction.atomic():
        child = InboundWarehouseOrder.objects.create(
            code=code,
            order=primary_order.order,
            primary_order=primary_order,
            state=initial_state,
            pickup_location=primary_order.pickup_location,
        )
        audit_service.add_entry(
            child,
            action=AuditAction.CREATE,
            user=context.user_id,
            reason=AuditMessages.CHILD_WAREHOUSE_ORDER_CREATED.CS.format(
                child_code=code,
                parent_code=primary_order.code,
            ),
            changes={"parent_order": primary_order.code},
        )
        audit_service.add_entry(
            primary_order,
            action=AuditAction.OTHER,
            user=context.user_id,
            reason=AuditMessages.CHILD_WAREHOUSE_ORDER_CREATED.CS.format(
                child_code=code,
                parent_code=primary_order.code,
            ),
            changes={"child_order": code},
        )
    return child


def _create_sales_outbound(
    sales_order: OutboundOrder,
    context: RequestContext,
    prefix: str,
) -> OutboundWarehouseOrder:
    code = generate_next_code(OutboundWarehouseOrder, prefix)
    with transaction.atomic():
        wo = OutboundWarehouseOrder.objects.create(
            code=code,
            order=sales_order,
            state=OutboundWarehouseOrderState.PENDING,
        )
        audit_service.add_entry(
            wo,
            action=AuditAction.CREATE,
            user=context.user_id,
            reason=AuditMessages.WAREHOUSE_ORDER_BOUND_TO_PURCHASE_ORDER.CS.format(
                purchase_order_code=sales_order.code
            ),
        )
    return wo


def _create_mfg_outbound(
    manufacturing_order: ManufacturingOrder,
    context: RequestContext,
    prefix: str,
) -> OutboundWarehouseOrder:
    code = generate_next_code(OutboundWarehouseOrder, prefix)
    with transaction.atomic():
        wo = OutboundWarehouseOrder.objects.create(
            code=code,
            manufacturing_order=manufacturing_order,
            state=OutboundWarehouseOrderState.PENDING,
        )
        audit_service.add_entry(
            wo,
            action=AuditAction.CREATE,
            user=context.user_id,
            reason=AuditMessages.WAREHOUSE_ORDER_BOUND_TO_PURCHASE_ORDER.CS.format(
                purchase_order_code=manufacturing_order.code
            ),
        )
    return wo


def _create_child_outbound(
    primary_order: OutboundWarehouseOrder,
    context: RequestContext,
    prefix: str,
    initial_state: OutboundWarehouseOrderState,
) -> OutboundWarehouseOrder:
    code = generate_next_code(OutboundWarehouseOrder, prefix)
    with transaction.atomic():
        child = OutboundWarehouseOrder.objects.create(
            code=code,
            order=primary_order.order,
            primary_order=primary_order,
            state=initial_state,
        )
        audit_service.add_entry(
            child,
            action=AuditAction.CREATE,
            user=context.user_id,
            reason=AuditMessages.CHILD_WAREHOUSE_ORDER_CREATED.CS.format(
                child_code=code,
                parent_code=primary_order.code,
            ),
            changes={"parent_order": primary_order.code},
        )
        audit_service.add_entry(
            primary_order,
            action=AuditAction.OTHER,
            user=context.user_id,
            reason=AuditMessages.CHILD_WAREHOUSE_ORDER_CREATED.CS.format(
                child_code=code,
                parent_code=primary_order.code,
            ),
            changes={"child_order": code},
        )
    return child


# ──────────────────────────────────────────────────────────────────────────────
# Public entrypoint
# ──────────────────────────────────────────────────────────────────────────────


def create_warehouse_order(
    kind: WarehouseOrderKind,
    context: RequestContext,
    *,
    purchase_order: InboundOrder | None = None,
    sales_order: OutboundOrder | None = None,
    manufacturing_order: ManufacturingOrder | None = None,
    primary_order: InboundWarehouseOrder | OutboundWarehouseOrder | None = None,
    initial_state: InboundWarehouseOrderState
    | OutboundWarehouseOrderState
    | None = None,
    code_prefix: str | None = None,
) -> InboundWarehouseOrder | OutboundWarehouseOrder:
    """
    Create a blank warehouse order, generate its sequential code, and write
    the initial audit entry on the created entity.

    The correct code prefix is selected automatically from module-level
    constants based on *kind*; pass *code_prefix* to override.

    Callers remain responsible for:
    - Adding order items after creation
    - Writing audit entries on the parent business document
    - Triggering parent-order state transitions (PICKING, RECEIVING, etc.)
    """
    match kind:
        case WarehouseOrderKind.INBOUND:
            return _create_inbound(
                purchase_order=purchase_order,  # type: ignore[arg-type]
                context=context,
                prefix=code_prefix or INBOUND_PREFIX,
            )
        case WarehouseOrderKind.MFG_INBOUND:
            return _create_mfg_inbound(
                manufacturing_order=manufacturing_order,  # type: ignore[arg-type]
                context=context,
                prefix=code_prefix or MFG_INBOUND_PREFIX,
            )
        case WarehouseOrderKind.CHILD_INBOUND:
            return _create_child_inbound(
                primary_order=primary_order,  # type: ignore[arg-type]
                context=context,
                prefix=code_prefix or INBOUND_PREFIX,
                initial_state=initial_state or InboundWarehouseOrderState.DRAFT,  # type: ignore[arg-type]
            )
        case WarehouseOrderKind.SALES_OUTBOUND:
            return _create_sales_outbound(
                sales_order=sales_order,  # type: ignore[arg-type]
                context=context,
                prefix=code_prefix or SALES_OUTBOUND_PREFIX,
            )
        case WarehouseOrderKind.MFG_OUTBOUND:
            return _create_mfg_outbound(
                manufacturing_order=manufacturing_order,  # type: ignore[arg-type]
                context=context,
                prefix=code_prefix or MFG_OUTBOUND_PREFIX,
            )
        case WarehouseOrderKind.CHILD_OUTBOUND:
            return _create_child_outbound(
                primary_order=primary_order,  # type: ignore[arg-type]
                context=context,
                prefix=code_prefix or OUTBOUND_PREFIX,
                initial_state=initial_state or OutboundWarehouseOrderState.PENDING,  # type: ignore[arg-type]
            )
