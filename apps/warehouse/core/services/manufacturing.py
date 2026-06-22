from calendar import monthrange
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from loguru import logger

from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.exceptions import (
    WarehouseItemBadRequestError,
    WarehouseOrderNotEditableError,
)
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.manufacturing import (
    ManufacturingOrderCreateOrUpdateSchema,
    ManufacturingOrderItemCreateSchema,
    ManufacturingOrderItemSchema,
    ManufacturingOrderSchema,
)
from apps.warehouse.core.services import audit_service
from apps.warehouse.core.transformation import (
    manufacturing_order_item_orm_to_schema,
    manufacturing_order_orm_to_schema,
)
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.manufacturing import (
    ManufacturingOrder,
    ManufacturingOrderItem,
    ManufacturingOrderState,
)
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    InboundWarehouseOrderState,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderItem,
    OutboundWarehouseOrderState,
)


def _get_end_of_month(date: datetime) -> datetime:
    last_day = monthrange(date.year, date.month)[1]
    return date.replace(day=last_day)


def _get_month_range(date: datetime) -> tuple[datetime, datetime]:
    last_day = _get_end_of_month(date)
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0), last_day


class ManufacturingOrdersService:
    @staticmethod
    def generate_next_code() -> str:
        now = timezone.now()
        dt_range = _get_month_range(now)
        monthly_prefix = f"PV{now.year}{now.month:02d}"
        last_code = (
            ManufacturingOrder.objects.filter(
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

    @staticmethod
    def generate_next_outbound_warehouse_order_code() -> str:
        now = timezone.now()
        dt_range = _get_month_range(now)
        count = OutboundWarehouseOrder.objects.filter(created__range=dt_range).count()
        return f"V{now.year}{now.month:02d}{count + 1:04d}"

    @staticmethod
    def generate_next_inbound_warehouse_order_code() -> str:
        now = timezone.now()
        dt_range = _get_month_range(now)
        count = InboundWarehouseOrder.objects.filter(created__range=dt_range).count()
        return f"P{now.year}{now.month:02d}{count + 1:04d}"

    @staticmethod
    def get_manufacturing_orders(
        search_term: str | None = None,
        state: str | None = None,
    ) -> QuerySet[ManufacturingOrder]:
        qs = ManufacturingOrder.objects.select_related("customer").exclude(
            state__in=[
                ManufacturingOrderState.CANCELLED,
                ManufacturingOrderState.COMPLETED,
            ]
        )
        if search_term:
            qs = qs.filter(code__icontains=search_term)
        if state:
            state_map = {
                "draft": ManufacturingOrderState.DRAFT,
                "confirmed": ManufacturingOrderState.CONFIRMED,
                "in_progress": ManufacturingOrderState.IN_PROGRESS,
                "completed": ManufacturingOrderState.COMPLETED,
                "cancelled": ManufacturingOrderState.CANCELLED,
            }
            if state in state_map:
                qs = qs.filter(state=state_map[state])
        return qs

    @staticmethod
    def _is_editable(order: ManufacturingOrder) -> bool:
        return order.state == ManufacturingOrderState.DRAFT

    @classmethod
    def _ensure_editable(cls, order: ManufacturingOrder) -> None:
        if not cls._is_editable(order):
            raise WarehouseOrderNotEditableError(
                f"Manufacturing order '{order.code}' is not editable in state '{ManufacturingOrderState(order.state)}'."
            )

    @classmethod
    def create_or_update(
        cls,
        params: ManufacturingOrderCreateOrUpdateSchema,
        context: RequestContext,
        code: str | None = None,
    ) -> ManufacturingOrderSchema:
        if code is None:
            code = cls.generate_next_code()

        existing = ManufacturingOrder.objects.filter(code=code).first()
        if existing:
            cls._ensure_editable(existing)

        customer = None
        if params.customer_code:
            customer = Customer.objects.get(code=params.customer_code)

        supplier = None
        if params.supplier_code:
            supplier = Customer.objects.get(code=params.supplier_code)

        with transaction.atomic():
            order, created = ManufacturingOrder.objects.update_or_create(
                code=code,
                defaults=dict(
                    description=params.description,
                    note=params.note,
                    is_external=params.is_external,
                    customer=customer,
                    supplier=supplier,
                ),
            )
            if created:
                audit_service.add_entry(
                    order,
                    action=AuditAction.CREATE,
                    user=context.user_id,
                    reason=AuditMessages.NEW_MANUFACTURING_ORDER_CREATED.CS,
                )
            else:
                audit_service.add_entry(
                    order,
                    action=AuditAction.UPDATE,
                    user=context.user_id,
                    reason=AuditMessages.MANUFACTURING_ORDER_UPDATED.CS,
                )

        return manufacturing_order_orm_to_schema(order)

    @classmethod
    def add_item(
        cls,
        code: str,
        item: ManufacturingOrderItemCreateSchema,
        context: RequestContext,
    ) -> ManufacturingOrderItemSchema:
        order = ManufacturingOrder.objects.get(code=code)
        cls._ensure_editable(order)

        in_product = StockProduct.objects.get(code=item.in_product_code)
        out_product = StockProduct.objects.get(code=item.out_product_code)

        with transaction.atomic():
            next_index = order.items.count()
            item_model = ManufacturingOrderItem.objects.create(
                order=order,
                in_product=in_product,
                in_amount=Decimal(str(item.in_amount)),
                out_product=out_product,
                out_amount=Decimal(str(item.out_amount)),
                index=item.index if item.index is not None else next_index,
            )

        return manufacturing_order_item_orm_to_schema(item_model)

    @classmethod
    def update_item(
        cls,
        code: str,
        item_id: int,
        item: ManufacturingOrderItemCreateSchema,
        context: RequestContext,
    ) -> ManufacturingOrderItemSchema:
        order = ManufacturingOrder.objects.get(code=code)
        cls._ensure_editable(order)

        in_product = StockProduct.objects.get(code=item.in_product_code)
        out_product = StockProduct.objects.get(code=item.out_product_code)

        with transaction.atomic():
            item_model = ManufacturingOrderItem.objects.get(pk=item_id, order=order)
            item_model.in_product = in_product
            item_model.in_amount = Decimal(str(item.in_amount))
            item_model.out_product = out_product
            item_model.out_amount = Decimal(str(item.out_amount))
            if item.index is not None:
                item_model.index = item.index
            item_model.save()

        return manufacturing_order_item_orm_to_schema(item_model)

    @classmethod
    def remove_item(cls, code: str, item_id: int, context: RequestContext) -> bool:
        order = ManufacturingOrder.objects.get(code=code)
        cls._ensure_editable(order)
        with transaction.atomic():
            ManufacturingOrderItem.objects.filter(pk=item_id, order=order).delete()
        return True

    @classmethod
    def transition_order(
        cls,
        code: str,
        context: RequestContext,
        action: str = "next",
    ) -> ManufacturingOrderSchema:
        order = ManufacturingOrder.objects.get(code=code)
        old_state = ManufacturingOrderState(order.state)

        if action == "cancel":
            if old_state in (
                ManufacturingOrderState.COMPLETED,
                ManufacturingOrderState.CANCELLED,
            ):
                raise WarehouseItemBadRequestError(
                    f"Cannot cancel manufacturing order '{code}' in state '{old_state}'."
                )
            new_state = ManufacturingOrderState.CANCELLED
        elif action == "next":
            if old_state == ManufacturingOrderState.DRAFT:
                if not order.items.exists():
                    raise WarehouseItemBadRequestError(
                        "Manufacturing order must have at least one item before confirmation."
                    )
                new_state = ManufacturingOrderState.CONFIRMED
            elif old_state == ManufacturingOrderState.CONFIRMED:
                new_state = ManufacturingOrderState.IN_PROGRESS
            elif old_state == ManufacturingOrderState.IN_PROGRESS:
                new_state = ManufacturingOrderState.COMPLETED
            else:
                raise WarehouseItemBadRequestError(
                    f"No next transition from state '{old_state}'."
                )
        else:
            raise WarehouseItemBadRequestError(f"Unsupported action '{action}'.")

        with transaction.atomic():
            order.state = new_state

            if new_state == ManufacturingOrderState.CANCELLED:
                order.cancelled_date = timezone.now()
            if new_state == ManufacturingOrderState.COMPLETED:
                order.completed_date = timezone.now()

            order.save()

            logger.info(
                f"Manufacturing order '{code}' transitioned: {old_state} -> {new_state}"
            )
            audit_service.add_entry(
                order,
                action=AuditAction.TRANSITION,
                user=context.user_id,
                reason=AuditMessages.MANUFACTURING_ORDER_STATE_CHANGED.CS.format(
                    old_state=old_state, new_state=new_state
                ),
                changes={"state": {"old": str(old_state), "new": str(new_state)}},
            )

            # On confirmation: create outbound warehouse order to dispatch IN products
            if new_state == ManufacturingOrderState.CONFIRMED:
                cls._create_outbound_warehouse_order(order, context)

            # On in_progress: create inbound warehouse order for OUT products return
            if new_state == ManufacturingOrderState.IN_PROGRESS:
                cls._create_inbound_warehouse_order(order, context)

        order.refresh_from_db()
        return manufacturing_order_orm_to_schema(order)

    @classmethod
    def _create_outbound_warehouse_order(
        cls, order: ManufacturingOrder, context: RequestContext
    ) -> OutboundWarehouseOrder:
        wo_code = cls.generate_next_outbound_warehouse_order_code()
        warehouse_order = OutboundWarehouseOrder.objects.create(
            code=wo_code,
            manufacturing_order=order,
            state=OutboundWarehouseOrderState.DRAFT,
        )

        for index, item in enumerate(order.items.order_by("index", "created")):
            OutboundWarehouseOrderItem.objects.create(
                warehouse_order=warehouse_order,
                source_manufacturing_item=item,
                stock_product=item.in_product,
                amount=item.in_amount,
                index=index,
            )

        audit_service.add_entry(
            order,
            action=AuditAction.UPDATE,
            user=context.user_id,
            reason=AuditMessages.MANUFACTURING_OUTBOUND_ORDER_CREATED.CS.format(
                code=wo_code
            ),
            changes={"outbound_warehouse_order": {"created": wo_code}},
        )
        return warehouse_order

    @classmethod
    def _create_inbound_warehouse_order(
        cls, order: ManufacturingOrder, context: RequestContext
    ) -> InboundWarehouseOrder:
        wo_code = cls.generate_next_inbound_warehouse_order_code()
        warehouse_order = InboundWarehouseOrder.objects.create(
            code=wo_code,
            manufacturing_order=order,
            state=InboundWarehouseOrderState.IN_TRANSIT,
        )

        audit_service.add_entry(
            order,
            action=AuditAction.UPDATE,
            user=context.user_id,
            reason=AuditMessages.MANUFACTURING_INBOUND_ORDER_CREATED.CS.format(
                code=wo_code
            ),
            changes={"inbound_warehouse_order": {"created": wo_code}},
        )
        return warehouse_order


manufacturing_orders_service = ManufacturingOrdersService()
