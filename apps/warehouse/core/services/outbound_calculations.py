from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from loguru import logger

from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.orders import (
    OutboundCalculationCreateOrUpdateSchema,
    OutboundCalculationSchema,
    OutboundOrderItemCreateSchema,
    OutboundOrderItemSchema,
    OutboundOrderSchema,
)
from apps.warehouse.core.services import audit_service
from apps.warehouse.core.services.item_reorder import (
    compact_order_items,
    reorder_order_items,
)
from apps.warehouse.core.services.outbound_common import (
    build_item_pricing_details,
    compute_unit_price,
    diff_schemas,
    generate_next_monthly_code,
    get_customer_contact_or_none,
    get_desired_batch_or_none,
    get_desired_package_or_none,
    validate_desired_packaging,
    with_pricing_details,
)
from apps.warehouse.core.services.outbound_orders import outbound_orders_service
from apps.warehouse.core.services.settings import settings_service
from apps.warehouse.core.transformation import (
    outbound_calculation_orm_to_schema,
    outbound_order_item_orm_to_schema,
    outbound_order_orm_to_schema,
)
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.orders import (
    OutboundCalculation,
    OutboundCalculationItem,
    OutboundCalculationState,
    OutboundOrder,
    OutboundOrderItem,
    OutboundOrderState,
)
from apps.warehouse.models.product import StockProduct


class OutboundCalculationsService:
    """
    Calculations are offers made to a client before the deal is struck. They are
    freely editable while open and never touch the warehouse. After the buyer
    confirms, `create_order` flips one over to a real `OutboundOrder`.
    """

    @staticmethod
    def _get_active(code: str) -> OutboundCalculation:
        return (
            OutboundCalculation.objects.active()
            .select_related("customer", "supplier", "contact", "order")
            .get(code=code)
        )

    @staticmethod
    def _to_schema(calculation: OutboundCalculation) -> OutboundCalculationSchema:
        schema = outbound_calculation_orm_to_schema(calculation)
        return with_pricing_details(schema, calculation)

    @staticmethod
    def get_calculation(code: str) -> OutboundCalculationSchema:
        return OutboundCalculationsService._to_schema(
            OutboundCalculationsService._get_active(code)
        )

    @staticmethod
    def get_calculations(
        search_term: str | None = None,
        stock_product_code: str | None = None,
        customer_code: str | None = None,
        include_all: bool = False,
    ):
        """Non-deleted calculations; closed ones only with `include_all` or a search."""
        qs = OutboundCalculation.objects.active().select_related(
            "customer", "supplier", "contact", "order"
        )
        if not include_all and not search_term:
            qs = qs.filter(state=OutboundCalculationState.OPEN)

        if search_term:
            qs = qs.filter(
                Q(code__icontains=search_term)
                | Q(customer__name__icontains=search_term)
                | Q(order__code__icontains=search_term)
            )

        if stock_product_code:
            qs = qs.filter(items__stock_product__code=stock_product_code).distinct()

        if customer_code:
            qs = qs.filter(customer__code=customer_code)

        return qs

    @staticmethod
    def generate_next_calculation_code() -> str:
        return generate_next_monthly_code(
            queryset=OutboundCalculation.objects.all(),
            field_name="code",
            prefix="K",
        )

    @staticmethod
    def _assert_editable(calculation: OutboundCalculation) -> None:
        if calculation.state != OutboundCalculationState.OPEN:
            raise WarehouseItemBadRequestError(
                f"Calculation '{calculation.code}' is closed and can no longer be edited."
            )

    @classmethod
    def update_or_create(
        cls,
        params: OutboundCalculationCreateOrUpdateSchema,
        context: RequestContext,
        code: str | None = None,
    ) -> OutboundCalculationSchema:
        calculation = None
        previous_schema = None
        if code is not None:
            calculation = cls._get_active(code)
            cls._assert_editable(calculation)
            previous_schema = outbound_calculation_orm_to_schema(calculation)

        customer = Customer.objects.get(code=params.customer_code)
        contact = get_customer_contact_or_none(customer, params.contact_id)
        values = dict(
            external_code=params.external_code,
            description=params.description,
            note=params.note,
            currency=params.currency,
            customer=customer,
            contact=contact,
            requested_delivery_date=params.requested_delivery_date,
        )

        with transaction.atomic():
            if calculation is None:
                calculation = OutboundCalculation.objects.create(
                    code=cls.generate_next_calculation_code(), **values
                )
                audit_service.add_entry(
                    calculation,
                    action=AuditAction.CREATE,
                    user=context.user_id,
                    reason=AuditMessages.CALCULATION_CREATED.CS,
                )
            else:
                for field, value in values.items():
                    setattr(calculation, field, value)
                calculation.save()
                assert previous_schema is not None
                audit_service.add_entry(
                    calculation,
                    action=AuditAction.UPDATE,
                    user=context.user_id,
                    reason=AuditMessages.CALCULATION_UPDATED.CS,
                    changes=diff_schemas(
                        previous_schema, outbound_calculation_orm_to_schema(calculation)
                    ),
                )

        return cls._to_schema(calculation)

    @classmethod
    def add_item(
        cls,
        code: str,
        item: OutboundOrderItemCreateSchema,
    ) -> OutboundOrderItemSchema:
        calculation = cls._get_active(code)
        cls._assert_editable(calculation)
        stock_product = StockProduct.objects.get(code=item.product_code)
        desired_package_type = get_desired_package_or_none(
            item.desired_package_type_name
        )
        desired_batch = get_desired_batch_or_none(item.desired_batch_code)
        amount = Decimal(str(item.amount))

        with transaction.atomic():
            # lock the calculation row to serialize concurrent index allocation
            OutboundCalculation.objects.select_for_update().get(pk=calculation.pk)
            total_price = settings_service.apply_minimum_item_value(
                calculation.customer, Decimal(str(item.total_price))
            )
            validate_desired_packaging(
                stock_product=stock_product,
                amount=amount,
                desired_package_type=desired_package_type,
            )
            item_model = OutboundCalculationItem.objects.create(
                stock_product=stock_product,
                amount=amount,
                calculation=calculation,
                total_price=total_price,
                unit_price=compute_unit_price(amount, total_price),
                index=item.index
                if item.index is not None
                else calculation.items.count(),
                desired_package_type=desired_package_type,
                desired_batch=desired_batch,
                note=item.note,
            )
        return cls._item_to_schema(calculation, item_model)

    @classmethod
    def update_item(
        cls,
        code: str,
        item_index: int,
        item: OutboundOrderItemCreateSchema,
    ) -> OutboundOrderItemSchema:
        calculation = cls._get_active(code)
        cls._assert_editable(calculation)
        item_model = OutboundCalculationItem.objects.get(
            calculation=calculation, index=item_index
        )
        desired_package_type = get_desired_package_or_none(
            item.desired_package_type_name
        )
        desired_batch = get_desired_batch_or_none(item.desired_batch_code)
        amount = Decimal(str(item.amount))

        with transaction.atomic():
            total_price = settings_service.apply_minimum_item_value(
                calculation.customer, Decimal(str(item.total_price))
            )
            validate_desired_packaging(
                stock_product=item_model.stock_product,
                amount=amount,
                desired_package_type=desired_package_type,
            )
            item_model.amount = amount
            item_model.total_price = total_price
            item_model.unit_price = compute_unit_price(amount, total_price)
            item_model.desired_package_type = desired_package_type
            item_model.desired_batch = desired_batch
            item_model.note = item.note
            if item.index is not None:
                item_model.index = item.index
            item_model.save()
        return cls._item_to_schema(calculation, item_model)

    @classmethod
    def remove_item(cls, code: str, item_index: int) -> OutboundCalculationSchema:
        calculation = cls._get_active(code)
        cls._assert_editable(calculation)
        item_model = OutboundCalculationItem.objects.get(
            calculation=calculation, index=item_index
        )
        with transaction.atomic():
            OutboundCalculation.objects.select_for_update().get(pk=calculation.pk)
            item_model.delete()
            compact_order_items(calculation.items.select_for_update())
        return cls.get_calculation(code)

    @classmethod
    def reorder_item(
        cls, code: str, item_index: int, new_index: int
    ) -> OutboundCalculationSchema:
        calculation = cls._get_active(code)
        cls._assert_editable(calculation)
        with transaction.atomic():
            reorder_order_items(
                calculation.items.select_for_update(), item_index, new_index
            )
        return cls.get_calculation(code)

    @staticmethod
    def _item_to_schema(
        calculation: OutboundCalculation, item_model: OutboundCalculationItem
    ) -> OutboundOrderItemSchema:
        pricing_details = build_item_pricing_details(
            order=calculation,
            stock_product=item_model.stock_product,
            selected_unit_price=item_model.unit_price,
            total_price=item_model.total_price,
        )
        return outbound_order_item_orm_to_schema(
            item_model, pricing_details=pricing_details
        )

    @classmethod
    def transition(
        cls, code: str, context: RequestContext, action: str
    ) -> OutboundCalculationSchema:
        with transaction.atomic():
            calculation = cls._get_active(code)
            if action == "close":
                new_state = OutboundCalculationState.CLOSED
            elif action == "reopen":
                if calculation.order_id is not None:
                    raise WarehouseItemBadRequestError(
                        f"Calculation '{code}' already has order "
                        f"'{calculation.order.code}' and cannot be reopened."  # type: ignore[union-attr]
                    )
                new_state = OutboundCalculationState.OPEN
            else:
                raise WarehouseItemBadRequestError(
                    f"Unsupported transition action '{action}'"
                )
            cls._set_state(calculation, new_state, context)
        return cls._to_schema(calculation)

    @staticmethod
    def _set_state(
        calculation: OutboundCalculation,
        new_state: OutboundCalculationState,
        context: RequestContext,
    ) -> None:
        old_state = OutboundCalculationState(calculation.state)
        if old_state == new_state:
            return
        calculation.state = new_state
        calculation.save(update_fields=["state", "changed"])
        audit_service.add_entry(
            calculation,
            action=AuditAction.TRANSITION,
            user=context.user_id,
            reason=AuditMessages.CALCULATION_STATE_CHANGED.CS.format(
                old_state=old_state, new_state=new_state
            ),
            changes={"state": {"old": old_state, "new": new_state}},
        )

    @classmethod
    def delete(cls, code: str, context: RequestContext) -> None:
        """Soft delete: the row (and its items) stay, it just disappears from the app."""
        calculation = cls._get_active(code)
        calculation.is_deleted = True
        calculation.deleted_date = timezone.now()
        calculation.save(update_fields=["is_deleted", "deleted_date", "changed"])
        audit_service.add_entry(
            calculation,
            action=AuditAction.DELETE,
            user=context.user_id,
            reason=AuditMessages.CALCULATION_DELETED.CS,
        )
        logger.info(f"Calculation '{code}' deleted")

    @classmethod
    def duplicate(
        cls, source_code: str, context: RequestContext
    ) -> OutboundCalculationSchema:
        source = cls._get_active(source_code)
        with transaction.atomic():
            new_calculation = OutboundCalculation.objects.create(
                code=cls.generate_next_calculation_code(),
                external_code=source.external_code,
                description=source.description,
                note=source.note,
                currency=source.currency,
                customer=source.customer,
                contact=source.contact,
                supplier=source.supplier,
                requested_delivery_date=source.requested_delivery_date,
            )
            OutboundCalculationItem.objects.bulk_create(
                OutboundCalculationItem(
                    calculation=new_calculation,
                    stock_product=item.stock_product,
                    amount=item.amount,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                    index=item.index,
                    desired_package_type=item.desired_package_type,
                    desired_batch=item.desired_batch,
                    note=item.note,
                )
                for item in source.items.order_by("index")
            )
            audit_service.add_entry(
                new_calculation,
                action=AuditAction.CREATE,
                user=context.user_id,
                reason=AuditMessages.CALCULATION_CREATED.CS,
                changes={"duplicated_from": source_code},
            )
        return cls._to_schema(new_calculation)

    @classmethod
    def create_order(cls, code: str, context: RequestContext) -> OutboundOrderSchema:
        """
        Flip an open calculation over to an order: the order is a 1:1 mirror of the
        calculation (header and items), starts as SUBMITTED, and the calculation is
        kept as it is, only closed and linked to the order.
        """
        with transaction.atomic():
            calculation = cls._get_active(code)
            # re-read under lock, so that two clicks can't create two orders
            calculation = (
                OutboundCalculation.objects.select_for_update()
                .select_related("customer", "supplier", "contact", "order")
                .get(pk=calculation.pk)
            )
            if calculation.order_id is not None:
                raise WarehouseItemBadRequestError(
                    f"Calculation '{code}' already has order "
                    f"'{calculation.order.code}'."  # type: ignore[union-attr]
                )
            cls._assert_editable(calculation)
            items = list(
                calculation.items.select_related(
                    "stock_product", "desired_package_type", "desired_batch"
                ).order_by("index", "created")
            )
            if not items:
                raise WarehouseItemBadRequestError(
                    "Calculation must have at least one item before creating an order"
                )

            order = OutboundOrder.objects.create(
                code=outbound_orders_service.generate_next_outgoing_order_code(),
                external_code=calculation.external_code,
                description=calculation.description,
                note=calculation.note,
                currency=calculation.currency,
                customer=calculation.customer,
                supplier=calculation.supplier,
                contact=calculation.contact,
                requested_delivery_date=calculation.requested_delivery_date,
                state=OutboundOrderState.SUBMITTED,
            )
            OutboundOrderItem.objects.bulk_create(
                OutboundOrderItem(
                    order=order,
                    stock_product=item.stock_product,
                    amount=item.amount,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                    index=item.index,
                    desired_package_type=item.desired_package_type,
                    desired_batch=item.desired_batch,
                    note=item.note,
                )
                for item in items
            )
            calculation.order = order
            calculation.save(update_fields=["order", "changed"])
            cls._set_state(calculation, OutboundCalculationState.CLOSED, context)

            audit_service.add_entry(
                order,
                action=AuditAction.CREATE,
                user=context.user_id,
                reason=AuditMessages.ORDER_CREATED_FROM_CALCULATION.CS.format(
                    calculation_code=calculation.code
                ),
                changes={"created_from_calculation": calculation.code},
            )
            audit_service.add_entry(
                calculation,
                action=AuditAction.UPDATE,
                user=context.user_id,
                reason=AuditMessages.CALCULATION_CONVERTED_TO_ORDER.CS.format(
                    order_code=order.code
                ),
                changes={"order": {"old": None, "new": order.code}},
            )

        order = OutboundOrder.objects.select_related("customer", "calculation").get(
            pk=order.pk
        )
        return with_pricing_details(outbound_order_orm_to_schema(order), order)


outbound_calculations_service = OutboundCalculationsService()
