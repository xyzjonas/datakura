from decimal import Decimal
from typing import cast

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from loguru import logger

from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.invoice import InvoiceStoreSchema
from apps.warehouse.core.schemas.orders import (
    OutboundOrderCreateOrUpdateSchema,
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
from apps.warehouse.core.services.settings import settings_service
from apps.warehouse.core.services.warehouse_order_factory import (
    WarehouseOrderKind,
    create_warehouse_order,
)
from apps.warehouse.core.transformation import (
    outbound_order_item_orm_to_schema,
    outbound_order_orm_to_schema,
)
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.orders import (
    Invoice,
    InvoicePaymentMethod,
    OutboundOrder,
    OutboundOrderItem,
    OutboundOrderState,
)
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    OutboundWarehouseOrder,
    OutboundWarehouseOrderItem,
    OutboundWarehouseOrderState,
    WarehouseItem,
)


class OutboundOrdersService:
    _EDITABLE_WAREHOUSE_ORDER_STATES = (
        OutboundWarehouseOrderState.DRAFT,
        OutboundWarehouseOrderState.PENDING,
        OutboundWarehouseOrderState.STARTED,
    )

    @staticmethod
    def _has_completed_warehouse_order(order: OutboundOrder) -> bool:
        warehouse_orders = list(order.warehouse_orders.all())
        return bool(warehouse_orders) and all(
            warehouse_order.state == OutboundWarehouseOrderState.COMPLETED
            for warehouse_order in warehouse_orders
        )

    @staticmethod
    def _resolve_invoiced_state(invoice: Invoice) -> OutboundOrderState:
        if invoice.paid_date is not None:
            return OutboundOrderState.COMPLETED_PAID

        if invoice.due_date and invoice.due_date < timezone.localdate():
            return OutboundOrderState.WAITING_FOR_PAYMENT

        return OutboundOrderState.INVOICED

    @classmethod
    def sync_state_after_warehouse_completion(
        cls,
        order: OutboundOrder,
        context: RequestContext,
    ) -> None:
        if order.state == OutboundOrderState.CANCELLED:
            return

        target_state = OutboundOrderState.SENT
        if order.invoice_id is not None:
            invoice = order.invoice or Invoice.objects.get(pk=order.invoice_id)
            target_state = cls._resolve_invoiced_state(invoice)

        if order.state != target_state:
            cls.transition_order(
                order.code,
                context=context,
                target_state=target_state,
            )

    @classmethod
    def sync_state_from_invoice(
        cls,
        order: OutboundOrder,
        context: RequestContext,
    ) -> None:
        if order.state == OutboundOrderState.CANCELLED or order.invoice_id is None:
            return

        if not cls._has_completed_warehouse_order(order):
            raise WarehouseItemBadRequestError(
                f"Outbound order '{order.code}' must have completed warehouse order before invoicing."
            )

        invoice = order.invoice or Invoice.objects.get(pk=order.invoice_id)
        target_state = cls._resolve_invoiced_state(invoice)
        if order.state != target_state:
            cls.transition_order(
                order.code,
                context=context,
                target_state=target_state,
            )

    @classmethod
    def _build_outbound_warehouse_order_items(
        cls,
        *,
        warehouse_order: OutboundWarehouseOrder,
    ) -> None:
        linked_order = warehouse_order.order
        if linked_order is None:
            raise WarehouseItemBadRequestError(
                f"Outbound warehouse order '{warehouse_order.code}' has no linked order."
            )

        next_index = 0
        for order_item in linked_order.items.select_related(
            "stock_product",
            "desired_package_type",
            "desired_batch",
        ).order_by("index", "created"):
            remaining_amount = Decimal(str(order_item.amount))
            candidates = WarehouseItem.physical_stock.filter(
                stock_product=order_item.stock_product,
            ).order_by("created", "pk")

            if order_item.desired_package_type_id:
                candidates = candidates.filter(
                    package_type=order_item.desired_package_type,
                )

            if order_item.desired_batch_id:
                candidates = candidates.filter(batch=order_item.desired_batch)

            created_any = False
            for candidate in candidates:
                if remaining_amount <= 0:
                    break

                chunk_amount = min(remaining_amount, Decimal(str(candidate.amount)))
                OutboundWarehouseOrderItem.objects.create(
                    warehouse_order=warehouse_order,
                    source_order_item=order_item,
                    stock_product=order_item.stock_product,
                    amount=chunk_amount,
                    desired_package_type=order_item.desired_package_type,
                    desired_batch=order_item.desired_batch,
                    index=next_index,
                )
                created_any = True
                next_index += 1
                remaining_amount -= chunk_amount

            if remaining_amount > 0 or not created_any:
                OutboundWarehouseOrderItem.objects.create(
                    warehouse_order=warehouse_order,
                    source_order_item=order_item,
                    stock_product=order_item.stock_product,
                    amount=remaining_amount
                    if remaining_amount > 0
                    else order_item.amount,
                    desired_package_type=order_item.desired_package_type,
                    desired_batch=order_item.desired_batch,
                    index=next_index,
                )
                next_index += 1

    @staticmethod
    def get_outbound_order(code: str) -> OutboundOrderSchema:
        order = OutboundOrder.objects.select_related(
            "customer",
            "invoice__customer",
            "invoice__supplier",
            "invoice__payment_method",
        ).get(code=code)
        schema = outbound_order_orm_to_schema(order)
        return with_pricing_details(schema, order)

    @staticmethod
    def get_outbound_orders(
        search_term: str | None = None,
        stock_product_code: str | None = None,
        customer_code: str | None = None,
        include_all: bool = False,
    ) -> QuerySet[OutboundOrder]:
        qs = OutboundOrder.objects.select_related(
            "customer",
            "invoice__customer",
            "invoice__supplier",
            "invoice__payment_method",
        )
        if not include_all and not search_term:
            qs = qs.exclude(
                state__in=[
                    OutboundOrderState.CANCELLED,
                    OutboundOrderState.COMPLETED,
                    OutboundOrderState.COMPLETED_PAID,
                ]
            )

        if search_term:
            search_term = search_term.lower()
            qs = qs.filter(
                Q(code__iexact=search_term)
                | Q(code__icontains=search_term)
                | Q(calculation__code__icontains=search_term)
                | Q(customer__name__icontains=search_term)
            )

        if stock_product_code:
            qs = qs.filter(items__stock_product__code=stock_product_code).distinct()

        if customer_code:
            qs = qs.filter(customer__code=customer_code)

        return qs

    @staticmethod
    def _get_customer_or_none(customer_code: str | None) -> Customer | None:
        if not customer_code:
            return None
        return Customer.objects.get(code=customer_code)

    @classmethod
    def generate_next_outgoing_order_code(cls) -> str:
        return generate_next_monthly_code(
            queryset=OutboundOrder.objects.all(),
            field_name="code",
            prefix="OP",
        )

    @staticmethod
    def _assert_order_editable(order: OutboundOrder) -> None:
        if order.state in (
            OutboundOrderState.CANCELLED,
            OutboundOrderState.COMPLETED,
            OutboundOrderState.INVOICED,
            OutboundOrderState.WAITING_FOR_PAYMENT,
            OutboundOrderState.COMPLETED_PAID,
        ):
            raise WarehouseItemBadRequestError(
                f"Outbound order '{order.code}' can no longer be edited (state={order.state})."
            )

    @staticmethod
    def _requires_warehouse_sync(order: OutboundOrder) -> bool:
        return (
            order.warehouse_orders.exists()
            or order.state != OutboundOrderState.SUBMITTED
        )

    @classmethod
    def _find_open_warehouse_order(
        cls,
        order: OutboundOrder,
    ) -> OutboundWarehouseOrder | None:
        return (
            order.warehouse_orders.filter(
                state__in=cls._EDITABLE_WAREHOUSE_ORDER_STATES,
            )
            .order_by("-created", "-pk")
            .first()
        )

    @classmethod
    def _create_outbound_warehouse_order(
        cls,
        order: OutboundOrder,
        context: RequestContext,
        primary_order: OutboundWarehouseOrder | None = None,
    ) -> OutboundWarehouseOrder:
        if primary_order is None:
            warehouse_order = create_warehouse_order(
                WarehouseOrderKind.SALES_OUTBOUND,
                context,
                sales_order=order,
            )
        else:
            warehouse_order = create_warehouse_order(
                WarehouseOrderKind.CHILD_OUTBOUND,
                context,
                primary_order=primary_order,
            )

        outbound_orders_service.transition_order(
            order.code, context, target_state=OutboundOrderState.PICKING
        )

        return warehouse_order  # type: ignore[return-value]

    @classmethod
    def _ensure_editable_warehouse_order(
        cls,
        order: OutboundOrder,
        context: RequestContext,
    ) -> OutboundWarehouseOrder:
        open_order = cls._find_open_warehouse_order(order)
        if open_order is not None:
            return open_order

        latest_order = order.warehouse_orders.order_by("-created", "-pk").first()
        if latest_order is None:
            warehouse_order = cls._create_outbound_warehouse_order(order, context)
            cls._build_outbound_warehouse_order_items(warehouse_order=warehouse_order)
            return warehouse_order

        return cls._create_outbound_warehouse_order(
            order,
            context,
            primary_order=latest_order,
        )

    @staticmethod
    def _get_assigned_warehouse_requirements(
        order_item: OutboundOrderItem,
    ) -> QuerySet[OutboundWarehouseOrderItem]:
        return order_item.warehouse_order_items.filter(warehouse_item__isnull=False)

    @classmethod
    def _get_assigned_amount(cls, order_item: OutboundOrderItem) -> Decimal:
        return sum(
            (
                Decimal(str(requirement.amount))
                for requirement in cls._get_assigned_warehouse_requirements(order_item)
            ),
            Decimal(0),
        )

    @classmethod
    def _assert_assigned_requirements_compatible(
        cls,
        order_item: OutboundOrderItem,
    ) -> None:
        assigned_requirements = cls._get_assigned_warehouse_requirements(order_item)
        if not assigned_requirements.exists():
            return

        target_signature = (
            order_item.desired_package_type_id,
            order_item.desired_batch_id,
        )
        assigned_signatures = set(
            assigned_requirements.values_list(
                "desired_package_type_id",
                "desired_batch_id",
            )
        )
        if assigned_signatures != {target_signature}:
            raise WarehouseItemBadRequestError(
                "Assigned warehouse items prevent changing package or batch requirements."
            )

    @classmethod
    def _sync_order_item_to_warehouse_orders(
        cls,
        *,
        order: OutboundOrder,
        order_item: OutboundOrderItem,
        context: RequestContext,
    ) -> None:
        if not cls._requires_warehouse_sync(order):
            return

        cls._assert_assigned_requirements_compatible(order_item)

        assigned_amount = cls._get_assigned_amount(order_item)
        requested_amount = Decimal(str(order_item.amount))
        if requested_amount < assigned_amount:
            raise WarehouseItemBadRequestError(
                "Assigned warehouse items prevent decreasing amount below already assigned quantity."
            )

        remaining_amount = requested_amount - assigned_amount
        pending_requirements = list(
            order_item.warehouse_order_items.select_related("warehouse_order")
            .filter(
                warehouse_item__isnull=True,
                warehouse_order__state__in=cls._EDITABLE_WAREHOUSE_ORDER_STATES,
            )
            .order_by("created", "pk")
        )

        if remaining_amount == 0:
            if pending_requirements:
                OutboundWarehouseOrderItem.objects.filter(
                    pk__in=[requirement.pk for requirement in pending_requirements]
                ).delete()
            return

        target_order = cls._find_open_warehouse_order(order)
        if target_order is None:
            target_order = cls._ensure_editable_warehouse_order(order, context)

        primary_requirement = pending_requirements[0] if pending_requirements else None
        if primary_requirement is None:
            OutboundWarehouseOrderItem.objects.create(
                warehouse_order=target_order,
                source_order_item=order_item,
                stock_product=order_item.stock_product,
                amount=remaining_amount,
                desired_package_type=order_item.desired_package_type,
                desired_batch=order_item.desired_batch,
                index=order_item.index,
            )
        else:
            primary_requirement.warehouse_order = target_order
            primary_requirement.stock_product = order_item.stock_product
            primary_requirement.amount = remaining_amount
            primary_requirement.desired_package_type = order_item.desired_package_type
            primary_requirement.desired_batch = order_item.desired_batch
            primary_requirement.index = order_item.index
            primary_requirement.save(
                update_fields=[
                    "warehouse_order",
                    "stock_product",
                    "amount",
                    "desired_package_type",
                    "desired_batch",
                    "index",
                    "changed",
                ]
            )

        if len(pending_requirements) > 1:
            OutboundWarehouseOrderItem.objects.filter(
                pk__in=[requirement.pk for requirement in pending_requirements[1:]]
            ).delete()

    @staticmethod
    def update_or_create_outgoing(
        params: OutboundOrderCreateOrUpdateSchema,
        context: RequestContext,
        code: str | None = None,
    ) -> OutboundOrderSchema:
        if code is None:
            code = OutboundOrdersService.generate_next_outgoing_order_code()

        previous_order_schema = None
        existing_order = OutboundOrder.objects.filter(code=code).first()
        if existing_order:
            OutboundOrdersService._assert_order_editable(existing_order)
            previous_order_schema = outbound_order_orm_to_schema(existing_order)

        customer = Customer.objects.get(code=params.customer_code)
        contact = get_customer_contact_or_none(customer, params.contact_id)
        with transaction.atomic():
            order, created = OutboundOrder.objects.update_or_create(
                code=code,
                create_defaults=dict(
                    external_code=params.external_code,
                    description=params.description,
                    note=params.note,
                    currency=params.currency,
                    customer=customer,
                    contact=contact,
                    requested_delivery_date=params.requested_delivery_date,
                ),
                defaults=dict(
                    external_code=params.external_code,
                    description=params.description,
                    note=params.note,
                    currency=params.currency,
                    customer=customer,
                    contact=contact,
                    requested_delivery_date=params.requested_delivery_date,
                ),
            )
            if created:
                audit_service.add_entry(
                    order,
                    action=AuditAction.CREATE,
                    user=context.user_id,
                    reason=AuditMessages.ORDER_CREATED.CS,
                )
            else:
                if previous_order_schema:
                    audit_service.add_entry(
                        order,
                        user=context.user_id,
                        action=AuditAction.UPDATE,
                        reason=AuditMessages.ORDER_UPDATED.CS,
                        changes=diff_schemas(
                            previous_order_schema, outbound_order_orm_to_schema(order)
                        ),
                    )

        schema = outbound_order_orm_to_schema(order)
        return with_pricing_details(schema, order)

    @classmethod
    def add_item(
        cls,
        code: str,
        item: OutboundOrderItemCreateSchema,
        context: RequestContext,
    ) -> OutboundOrderItemSchema:
        order = OutboundOrder.objects.prefetch_related("warehouse_orders").get(
            code=code
        )
        cls._assert_order_editable(order)
        stock_product = StockProduct.objects.get(code=item.product_code)
        desired_package_type = get_desired_package_or_none(
            item.desired_package_type_name
        )
        desired_batch = get_desired_batch_or_none(item.desired_batch_code)

        with transaction.atomic():
            # lock the order row to serialize concurrent index allocation
            OutboundOrder.objects.select_for_update().get(pk=order.pk)
            next_index = order.items.count()
            amount = Decimal(str(item.amount))
            total_price = settings_service.apply_minimum_item_value(
                order.customer, Decimal(str(item.total_price))
            )
            validate_desired_packaging(
                stock_product=stock_product,
                amount=amount,
                desired_package_type=desired_package_type,
            )
            item_model = OutboundOrderItem.objects.create(
                stock_product=stock_product,
                amount=amount,
                order=order,
                total_price=total_price,
                unit_price=compute_unit_price(amount, total_price),
                index=item.index if item.index is not None else next_index,
                desired_package_type=desired_package_type,
                desired_batch=desired_batch,
                note=item.note,
            )
            cls._sync_order_item_to_warehouse_orders(
                order=order,
                order_item=item_model,
                context=context,
            )
        selected_unit_price = compute_unit_price(amount, total_price)
        pricing_details = build_item_pricing_details(
            order=order,
            stock_product=stock_product,
            selected_unit_price=selected_unit_price,
            total_price=total_price,
        )
        return outbound_order_item_orm_to_schema(
            item_model, pricing_details=pricing_details
        )

    @classmethod
    def update_item(
        cls,
        code: str,
        item_index: int,
        item: OutboundOrderItemCreateSchema,
        context: RequestContext,
    ) -> OutboundOrderItemSchema:
        order = OutboundOrder.objects.prefetch_related("warehouse_orders").get(
            code=code
        )
        cls._assert_order_editable(order)
        item_model = OutboundOrderItem.objects.get(order=order, index=item_index)
        desired_package_type = get_desired_package_or_none(
            item.desired_package_type_name
        )
        desired_batch = get_desired_batch_or_none(item.desired_batch_code)

        with transaction.atomic():
            amount = Decimal(str(item.amount))
            total_price = settings_service.apply_minimum_item_value(
                order.customer, Decimal(str(item.total_price))
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
            cls._sync_order_item_to_warehouse_orders(
                order=order,
                order_item=item_model,
                context=context,
            )
        pricing_details = build_item_pricing_details(
            order=order,
            stock_product=item_model.stock_product,
            selected_unit_price=item_model.unit_price,
            total_price=item_model.total_price,
        )
        return outbound_order_item_orm_to_schema(
            item_model, pricing_details=pricing_details
        )

    @classmethod
    def remove_item(
        cls,
        code: str,
        item_index: int,
        context: RequestContext,
    ) -> OutboundOrderSchema:
        order = OutboundOrder.objects.prefetch_related("warehouse_orders").get(
            code=code
        )
        cls._assert_order_editable(order)
        item_model = OutboundOrderItem.objects.get(
            order=order,
            index=item_index,
        )
        if cls._get_assigned_warehouse_requirements(item_model).exists():
            raise WarehouseItemBadRequestError(
                "Assigned warehouse items prevent removing this order item."
            )

        with transaction.atomic():
            OutboundOrder.objects.select_for_update().get(pk=order.pk)
            item_model.delete()
            compact_order_items(order.items.select_for_update())

        return cls.get_outbound_order(code)

    @classmethod
    def reorder_item(
        cls, code: str, item_index: int, new_index: int
    ) -> OutboundOrderSchema:
        order = OutboundOrder.objects.get(code=code)
        cls._assert_order_editable(order)
        with transaction.atomic():
            reorder_order_items(order.items.select_for_update(), item_index, new_index)

        schema = outbound_order_orm_to_schema(order)
        return with_pricing_details(schema, order)

    @classmethod
    def transition_order(
        cls,
        code: str,
        context: RequestContext,
        action: str = "next",
        target_state: OutboundOrderState | None = None,
    ) -> OutboundOrderSchema:
        order = OutboundOrder.objects.get(code=code)
        old_state = OutboundOrderState(order.state)

        if target_state is None:
            if action == "cancel":
                cls._assert_order_editable(order)
                new_state = OutboundOrderState.CANCELLED
                # Cancel all associated warehouse orders and release assignments (fix bug #2)
                for warehouse_order in order.warehouse_orders.all():
                    if warehouse_order.state != OutboundWarehouseOrderState.CANCELLED:
                        from apps.warehouse.core.services.warehouse import (
                            warehouse_service,
                        )

                        warehouse_service.cancel_outbound_warehouse_order(
                            warehouse_order, context
                        )
            elif action == "next":
                if old_state == OutboundOrderState.SUBMITTED:
                    if not order.items.exists():
                        raise WarehouseItemBadRequestError(
                            "Order must have at least one item before confirmation"
                        )
                    new_state = OutboundOrderState.PICKING
                elif old_state in (
                    OutboundOrderState.PICKING,
                    OutboundOrderState.PACKING,
                    OutboundOrderState.SHIPPING,
                ):
                    new_state = OutboundOrderState.SENT
                else:
                    raise WarehouseItemBadRequestError(
                        f"No next transition available from state '{old_state}'"
                    )
            else:
                raise WarehouseItemBadRequestError(
                    f"Unsupported transition action '{action}'"
                )
        else:
            new_state = target_state
            # If target_state is CANCELLED, also cancel warehouse orders (fix bug #12)
            if new_state == OutboundOrderState.CANCELLED:
                for warehouse_order in order.warehouse_orders.all():
                    if warehouse_order.state != OutboundWarehouseOrderState.CANCELLED:
                        from apps.warehouse.core.services.warehouse import (
                            warehouse_service,
                        )

                        warehouse_service.cancel_outbound_warehouse_order(
                            warehouse_order, context
                        )

        with transaction.atomic():
            order.state = new_state

            if (
                new_state == OutboundOrderState.PICKING
                and not order.warehouse_orders.exists()
            ):
                warehouse_order = cast(
                    OutboundWarehouseOrder,
                    create_warehouse_order(
                        WarehouseOrderKind.SALES_OUTBOUND,
                        context,
                        sales_order=order,
                    ),
                )
                cls._build_outbound_warehouse_order_items(
                    warehouse_order=warehouse_order  # type: ignore[arg-type]
                )

            if new_state in (
                OutboundOrderState.COMPLETED,
                OutboundOrderState.SENT,
                OutboundOrderState.INVOICED,
                OutboundOrderState.WAITING_FOR_PAYMENT,
                OutboundOrderState.COMPLETED_PAID,
            ):
                order.fulfilled_date = timezone.now()

            if new_state == OutboundOrderState.CANCELLED:
                order.cancelled_date = timezone.now()

            order.save()
            logger.info(
                f"Outbound order '{order.code}' transitioned: {old_state} -> {new_state}"
            )
            audit_service.add_entry(
                order,
                action=AuditAction.TRANSITION,
                user=context.user_id,
                reason=AuditMessages.OUTBOUND_ORDER_STATE_CHANGED.CS.format(
                    old_state=old_state, new_state=new_state
                ),
                changes={"state": {"old": old_state, "new": new_state}},
            )

        schema = outbound_order_orm_to_schema(order)
        return with_pricing_details(schema, order)

    @classmethod
    def duplicate_outbound_order(
        cls, source_code: str, context: RequestContext
    ) -> OutboundOrderSchema:
        source = OutboundOrder.objects.prefetch_related(
            "items__stock_product",
            "items__desired_package_type",
            "items__desired_batch",
        ).get(code=source_code)
        new_code = cls.generate_next_outgoing_order_code()

        with transaction.atomic():
            new_order = OutboundOrder.objects.create(
                code=new_code,
                external_code=source.external_code,
                description=source.description,
                note=source.note,
                currency=source.currency,
                customer=source.customer,
                contact=source.contact,
                supplier=source.supplier,
                requested_delivery_date=source.requested_delivery_date,
                state=OutboundOrderState.SUBMITTED,
            )
            for item in source.items.order_by("index"):
                OutboundOrderItem.objects.create(
                    order=new_order,
                    stock_product=item.stock_product,
                    amount=item.amount,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                    index=item.index,
                    desired_package_type=item.desired_package_type,
                    desired_batch=item.desired_batch,
                    note=item.note,
                )
            audit_service.add_entry(
                new_order,
                action=AuditAction.CREATE,
                user=context.user_id,
                reason=AuditMessages.ORDER_CREATED.CS,
                changes={"duplicated_from": source_code},
            )

        schema = outbound_order_orm_to_schema(new_order)
        return with_pricing_details(schema, new_order)

    @classmethod
    def store_invoice(
        cls,
        order_code: str,
        params: InvoiceStoreSchema,
        context: RequestContext,
        invoice_file: UploadedFile | None = None,
    ) -> OutboundOrderSchema:
        order = (
            OutboundOrder.objects.select_related("invoice")
            .prefetch_related("warehouse_orders")
            .get(code=order_code)
        )
        previous_invoice_code = order.invoice.code if order.invoice else None

        if not cls._has_completed_warehouse_order(order):
            raise WarehouseItemBadRequestError(
                f"Outbound order '{order.code}' must have completed warehouse order before invoicing."
            )

        customer = cls._get_customer_or_none(params.customer_code)
        supplier = cls._get_customer_or_none(params.supplier_code)
        payment_method = InvoicePaymentMethod.resolve(params.payment_method_name)

        with transaction.atomic():
            if order.invoice:
                invoice = order.invoice
            else:
                invoice = Invoice()

            invoice.customer = customer
            invoice.supplier = supplier
            invoice.code = params.code
            invoice.issued_date = params.issued_date
            invoice.due_date = params.due_date
            invoice.payment_method = payment_method
            invoice.external_code = params.external_code
            invoice.taxable_supply_date = params.taxable_supply_date
            invoice.paid_date = params.paid_date
            invoice.currency = params.currency
            invoice.note = params.note

            if invoice_file is not None:
                if invoice.pk and invoice.document:
                    invoice.document.delete(save=False)
                invoice.document = invoice_file

            invoice.save()

            if (order.invoice.pk if order.invoice else None) != invoice.pk:
                order.invoice = invoice
                order.save(update_fields=["invoice", "changed"])

            audit_service.add_entry(
                order,
                user=context.user_id,
                action=AuditAction.UPDATE,
                reason=AuditMessages.INVOICE_STORED_FOR_OUTBOUND_ORDER.CS.format(
                    invoice_code=invoice.code
                ),
                changes={
                    "invoice": {
                        "old": previous_invoice_code,
                        "new": invoice.code,
                    }
                },
            )

            cls.sync_state_from_invoice(order, context)

        order.refresh_from_db()
        schema = outbound_order_orm_to_schema(order)
        return with_pricing_details(schema, order)


outbound_orders_service = OutboundOrdersService()
