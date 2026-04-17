from calendar import monthrange
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from loguru import logger

from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.packaging import get_package_amount_in_product_uom
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.invoice import InvoiceStoreSchema
from apps.warehouse.core.schemas.orders import (
    OutboundOrderCreateOrUpdateSchema,
    OutboundOrderItemCreateSchema,
    OutboundOrderItemPricingDetailsSchema,
    OutboundOrderItemSchema,
    OutboundOrderSchema,
)
from apps.warehouse.core.services import audit_service
from apps.warehouse.core.services.products import stock_product_service
from apps.warehouse.core.transformation import (
    outbound_order_item_orm_to_schema,
    outbound_order_orm_to_schema,
)
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.barcode import Barcode
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.orders import (
    Invoice,
    InvoicePaymentMethod,
    OutboundOrder,
    OutboundOrderItem,
    OutboundOrderState,
)
from apps.warehouse.models.packaging import PackageType
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    Batch,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderItem,
    OutboundWarehouseOrderState,
    WarehouseItem,
)


def _get_end_of_month(date: datetime) -> datetime:
    last_day = monthrange(date.year, date.month)[1]
    return date.replace(day=last_day)


def _get_month_range(date: datetime) -> tuple[datetime, datetime]:
    last_day = _get_end_of_month(date)
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0), last_day


class OutboundOrdersService:
    @staticmethod
    def _get_desired_package_or_none(name: str | None) -> PackageType | None:
        if not name:
            return None
        return PackageType.objects.get(name=name)

    @staticmethod
    def _get_desired_batch_or_none(batch_code: str | None) -> Batch | None:
        if not batch_code:
            return None

        barcode = (
            Barcode.objects.select_related("content_type")
            .filter(code=batch_code)
            .first()
        )
        if not barcode or barcode.content_type.model_class() is not Batch:
            raise WarehouseItemBadRequestError(f"Batch '{batch_code}' does not exist.")
        return barcode.content_object  # type: ignore[return-value]

    @staticmethod
    def _validate_desired_packaging(
        *,
        stock_product: StockProduct,
        amount: Decimal,
        desired_package_type: PackageType | None,
    ) -> None:
        if desired_package_type is None:
            return

        package_amount = get_package_amount_in_product_uom(
            desired_package_type, stock_product
        )
        if not package_amount:
            raise WarehouseItemBadRequestError(
                f"Package '{desired_package_type.name}' cannot be converted to product '{stock_product.code}'."
            )

        normalized_package_amount = Decimal(str(package_amount))
        if normalized_package_amount <= 0:
            raise WarehouseItemBadRequestError(
                f"Package '{desired_package_type.name}' has invalid amount."
            )

        if amount % normalized_package_amount != 0:
            raise WarehouseItemBadRequestError(
                f"Requested amount '{amount}' does not fit package '{desired_package_type.name}'."
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
    def _with_pricing_details(
        order: OutboundOrderSchema, order_model: OutboundOrder
    ) -> OutboundOrderSchema:
        product_by_code = {
            item.stock_product.code: item.stock_product
            for item in order_model.items.select_related("stock_product")
        }
        for schema_item in order.items:
            product = product_by_code.get(schema_item.product.code)
            if product is None:
                continue
            schema_item.pricing_details = (
                OutboundOrdersService._build_item_pricing_details(
                    order=order_model,
                    stock_product=product,
                    selected_unit_price=Decimal(str(schema_item.unit_price)),
                )
            )
        return order

    @staticmethod
    def get_outbound_order(code: str) -> OutboundOrderSchema:
        order = OutboundOrder.objects.select_related("customer").get(code=code)
        schema = outbound_order_orm_to_schema(order)
        return OutboundOrdersService._with_pricing_details(schema, order)

    @staticmethod
    def _build_item_pricing_details(
        *,
        order: OutboundOrder,
        stock_product: StockProduct,
        selected_unit_price: Decimal,
    ) -> OutboundOrderItemPricingDetailsSchema:
        suggested = stock_product_service.get_selling_price_lookup(
            product_code=stock_product.code,
            customer_code=order.customer.code if order.customer else None,
        )

        avg_purchase_price = Decimal(str(stock_product.purchase_price or 0))
        margin_amount = selected_unit_price - avg_purchase_price
        margin_percent = Decimal("0")
        if avg_purchase_price > 0:
            margin_percent = (
                margin_amount / avg_purchase_price * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return OutboundOrderItemPricingDetailsSchema(
            base_price=suggested.base_price,
            avg_purchase_price=float(avg_purchase_price),
            suggested_unit_price=suggested.final_price,
            selected_unit_price=float(selected_unit_price),
            discount_percent=suggested.discount_percent,
            reason=suggested.reason,
            source=suggested.source,
            margin_amount=float(
                margin_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
            margin_percent=float(margin_percent),
        )

    @staticmethod
    def _compute_unit_price(amount: Decimal, total_price: Decimal) -> Decimal:
        if amount <= 0:
            return Decimal("0")
        return (total_price / amount).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

    @staticmethod
    def get_outbound_orders(
        search_term: str | None = None,
        stock_product_code: str | None = None,
    ) -> QuerySet[OutboundOrder]:
        qs = OutboundOrder.objects.select_related(
            "customer",
            "invoice__customer",
            "invoice__supplier",
            "invoice__payment_method",
        ).exclude(
            state__in=[OutboundOrderState.CANCELLED, OutboundOrderState.COMPLETED]
        )

        if search_term:
            search_term = search_term.lower()
            qs = qs.filter(
                Q(code__iexact=search_term)
                | Q(code__icontains=search_term)
                | Q(customer__name__icontains=search_term)
            )

        if stock_product_code:
            qs = qs.filter(items__stock_product__code=stock_product_code).distinct()

        return qs

    @staticmethod
    def _get_customer_or_none(customer_code: str | None) -> Customer | None:
        if not customer_code:
            return None
        return Customer.objects.get(code=customer_code)

    @staticmethod
    def generate_next_outgoing_order_code() -> str:
        now = timezone.now()
        dt_range = _get_month_range(now)
        orders_this_month = OutboundOrder.objects.filter(
            created__range=dt_range
        ).count()
        return f"OP{now.year}{now.month:02d}{orders_this_month + 1:04d}"

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
            previous_order_schema = outbound_order_orm_to_schema(existing_order)

        customer = Customer.objects.get(code=params.customer_code)
        with transaction.atomic():
            order, created = OutboundOrder.objects.update_or_create(
                code=code,
                defaults=dict(
                    external_code=params.external_code,
                    description=params.description,
                    note=params.note,
                    currency=params.currency,
                    customer=customer,
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
                    new_order = outbound_order_orm_to_schema(order).model_dump()
                    final_diff = {}
                    for key, value in previous_order_schema.model_dump().items():
                        if key in ("created", "changed"):
                            continue
                        if value != new_order[key]:
                            final_diff[key] = {
                                "old": str(value),
                                "new": str(new_order[key]),
                            }

                    audit_service.add_entry(
                        order,
                        user=context.user_id,
                        action=AuditAction.UPDATE,
                        reason=AuditMessages.ORDER_UPDATED.CS,
                        changes=final_diff,
                    )

        schema = outbound_order_orm_to_schema(order)
        return OutboundOrdersService._with_pricing_details(schema, order)

    @staticmethod
    def add_item(
        code: str, item: OutboundOrderItemCreateSchema
    ) -> OutboundOrderItemSchema:
        order = OutboundOrder.objects.get(code=code)
        stock_product = StockProduct.objects.get(code=item.product_code)
        desired_package_type = OutboundOrdersService._get_desired_package_or_none(
            item.desired_package_type_name
        )
        desired_batch = OutboundOrdersService._get_desired_batch_or_none(
            item.desired_batch_code
        )

        if OutboundOrderItem.objects.filter(
            order=order, stock_product=stock_product
        ).exists():
            raise WarehouseItemBadRequestError(
                f"Item for product '{stock_product.code}' already exists in order '{order.code}'"
            )

        with transaction.atomic():
            next_index = order.items.count()
            amount = Decimal(str(item.amount))
            total_price = Decimal(str(item.total_price))
            OutboundOrdersService._validate_desired_packaging(
                stock_product=stock_product,
                amount=amount,
                desired_package_type=desired_package_type,
            )
            item_model = OutboundOrderItem.objects.create(
                stock_product=stock_product,
                amount=amount,
                order=order,
                total_price=total_price,
                unit_price=OutboundOrdersService._compute_unit_price(
                    amount, total_price
                ),
                index=item.index if item.index is not None else next_index,
                desired_package_type=desired_package_type,
                desired_batch=desired_batch,
            )
        selected_unit_price = OutboundOrdersService._compute_unit_price(
            amount, total_price
        )
        pricing_details = OutboundOrdersService._build_item_pricing_details(
            order=order,
            stock_product=stock_product,
            selected_unit_price=selected_unit_price,
        )
        return outbound_order_item_orm_to_schema(
            item_model, pricing_details=pricing_details
        )

    @staticmethod
    def update_item(
        code: str, item: OutboundOrderItemCreateSchema
    ) -> OutboundOrderItemSchema:
        order = OutboundOrder.objects.get(code=code)
        item_model = OutboundOrderItem.objects.get(
            order=order, stock_product__code=item.product_code
        )
        desired_package_type = OutboundOrdersService._get_desired_package_or_none(
            item.desired_package_type_name
        )
        desired_batch = OutboundOrdersService._get_desired_batch_or_none(
            item.desired_batch_code
        )

        with transaction.atomic():
            amount = Decimal(str(item.amount))
            total_price = Decimal(str(item.total_price))
            OutboundOrdersService._validate_desired_packaging(
                stock_product=item_model.stock_product,
                amount=amount,
                desired_package_type=desired_package_type,
            )
            item_model.amount = amount
            item_model.total_price = total_price
            item_model.unit_price = OutboundOrdersService._compute_unit_price(
                amount, total_price
            )
            item_model.desired_package_type = desired_package_type
            item_model.desired_batch = desired_batch
            if item.index is not None:
                item_model.index = item.index
            item_model.save()
        pricing_details = OutboundOrdersService._build_item_pricing_details(
            order=order,
            stock_product=item_model.stock_product,
            selected_unit_price=item_model.unit_price,
        )
        return outbound_order_item_orm_to_schema(
            item_model, pricing_details=pricing_details
        )

    @staticmethod
    def remove_item(code: str, product_code: str) -> bool:
        order = OutboundOrder.objects.get(code=code)
        items = OutboundOrderItem.objects.filter(
            order=order, stock_product__code=product_code
        )
        with transaction.atomic():
            items.delete()

        return True

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
                new_state = OutboundOrderState.CANCELLED
            elif action == "next":
                if old_state in (
                    OutboundOrderState.DRAFT,
                    OutboundOrderState.SUBMITTED,
                ):
                    if not order.items.exists():
                        raise WarehouseItemBadRequestError(
                            "Order must have at least one item before confirmation"
                        )
                    new_state = OutboundOrderState.PICKING
                elif old_state == OutboundOrderState.PICKING:
                    new_state = OutboundOrderState.PACKING
                elif old_state == OutboundOrderState.PACKING:
                    new_state = OutboundOrderState.SHIPPING
                elif old_state == OutboundOrderState.SHIPPING:
                    new_state = OutboundOrderState.COMPLETED
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

        with transaction.atomic():
            order.state = new_state

            if (
                new_state == OutboundOrderState.PICKING
                and not order.warehouse_orders.exists()
            ):
                warehouse_order_code = cls.generate_next_outbound_warehouse_order_code()
                warehouse_order = OutboundWarehouseOrder.objects.create(
                    code=warehouse_order_code,
                    order=order,
                    state=OutboundWarehouseOrderState.PENDING,
                )
                audit_service.add_entry(
                    warehouse_order,
                    action=AuditAction.CREATE,
                    user=context.user_id,
                    reason=AuditMessages.WAREHOUSE_ORDER_BOUND_TO_PURCHASE_ORDER.CS.format(
                        purchase_order_code=code
                    ),
                )
                cls._build_outbound_warehouse_order_items(
                    warehouse_order=warehouse_order
                )

            if new_state == OutboundOrderState.COMPLETED:
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
                reason=AuditMessages.INBOUND_ORDER_STATE_CHANGED.CS.format(
                    old_state=old_state, new_state=new_state
                ),
                changes={"state": {"old": old_state, "new": new_state}},
            )

        schema = outbound_order_orm_to_schema(order)
        return OutboundOrdersService._with_pricing_details(schema, order)

    @staticmethod
    def generate_next_outbound_warehouse_order_code() -> str:
        now = timezone.now()
        dt_range = _get_month_range(now)
        count = OutboundWarehouseOrder.objects.filter(created__range=dt_range).count()
        return f"WO{now.year}{now.month:02d}{count + 1:04d}"

    @classmethod
    def store_invoice(
        cls,
        order_code: str,
        params: InvoiceStoreSchema,
        context: RequestContext,
        invoice_file: UploadedFile | None = None,
    ) -> OutboundOrderSchema:
        order = OutboundOrder.objects.select_related("invoice").get(code=order_code)
        previous_invoice_code = order.invoice.code if order.invoice else None

        customer = cls._get_customer_or_none(params.customer_code)
        supplier = cls._get_customer_or_none(params.supplier_code)
        payment_method, _ = InvoicePaymentMethod.objects.get_or_create(
            name=params.payment_method_name
        )

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
                reason=AuditMessages.INVOICE_STORED_FOR_INBOUND_ORDER.CS.format(
                    invoice_code=invoice.code
                ),
                changes={
                    "invoice": {
                        "old": previous_invoice_code,
                        "new": invoice.code,
                    }
                },
            )

        order.refresh_from_db()
        schema = outbound_order_orm_to_schema(order)
        return OutboundOrdersService._with_pricing_details(schema, order)


outbound_orders_service = OutboundOrdersService()
