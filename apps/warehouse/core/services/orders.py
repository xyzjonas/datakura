from calendar import monthrange
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Q, QuerySet
from django.template.loader import get_template
from django.utils import timezone
from loguru import logger

from apps.warehouse.core.exceptions import (
    WarehouseItemBadRequestError,
    WarehouseOrderNotEditableError,
)
from apps.warehouse.core.query_optimization import inbound_orders_for_schema
from apps.warehouse.core.schemas.certification import CertificationAttachSchema
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.credit_notes import CreditNoteSupplierSchema
from apps.warehouse.core.schemas.invoice import InvoiceStoreSchema
from apps.warehouse.core.schemas.orders import (
    InboundOrderItemCreateSchema,
    InboundOrderItemSchema,
    InboundOrderCreateOrUpdateSchema,
    InboundOrderSchema,
)
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.services import audit_service
from apps.warehouse.core.services.code_sequence import (
    generate_next_sequential_code,
)
from apps.warehouse.core.services.certifications import certifications_service
from apps.warehouse.core.services.item_reorder import (
    compact_order_items,
    reorder_order_items,
)
from apps.warehouse.core.services.pdf import print_html_to_pdf
from apps.warehouse.core.transformation import (
    inbound_order_item_orm_to_schema,
    inbound_order_orm_to_schema,
    credit_note_supplier_orm_to_schema,
)
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderItem,
    InboundOrderState,
    CreditNoteToSupplier,
    CreditNoteState,
    Invoice,
    InvoicePaymentMethod,
)
from apps.warehouse.models.product import StockProduct


def _get_end_of_month(date: datetime) -> datetime:
    last_day = monthrange(date.year, date.month)[1]
    return date.replace(day=last_day)


def _get_month_range(date: datetime) -> tuple[datetime, datetime]:
    last_day = _get_end_of_month(date)
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0), last_day


class OrdersService:
    @staticmethod
    def _compute_unit_price(amount: Decimal, total_price: Decimal) -> Decimal:
        if amount <= 0:
            return Decimal("0")
        return (total_price / amount).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

    @staticmethod
    def get_inbound_orders(
        search_term: str | None = None,
        stock_product_code: str | None = None,
        include_all: bool = False,
        supplier_code: str | None = None,
    ) -> QuerySet[InboundOrder]:
        qs = inbound_orders_for_schema()
        if not include_all and not search_term:
            qs = qs.exclude(
                state__in=[InboundOrderState.CANCELLED, InboundOrderState.COMPLETED]
            )

        if search_term:
            search_term = search_term.lower()
            qs = qs.filter(
                Q(code__iexact=search_term)
                | Q(code__icontains=search_term)
                | Q(supplier__name__icontains=search_term)
            )

        if stock_product_code:
            qs = qs.filter(items__stock_product__code=stock_product_code).distinct()

        if supplier_code:
            qs = qs.filter(supplier__code=supplier_code)

        return qs

    @staticmethod
    def _get_customer_or_none(customer_code: str | None) -> Customer | None:
        if not customer_code:
            return None
        return Customer.objects.get(code=customer_code)

    @staticmethod
    def _get_self_customer() -> Customer:
        try:
            return Customer.objects.get(is_self=True, is_deleted=False)
        except Customer.DoesNotExist as exc:
            raise WarehouseItemBadRequestError(
                "Set exactly one active customer as self before storing inbound invoices."
            ) from exc

    @staticmethod
    def _is_inbound_order_editable(order: InboundOrder) -> bool:
        return (
            order.state
            in (
                InboundOrderState.DRAFT,
                InboundOrderState.SUBMITTED,
            )
            and not order.warehouse_orders.exists()
        )

    @classmethod
    def _ensure_inbound_order_editable(cls, order: InboundOrder) -> None:
        if cls._is_inbound_order_editable(order):
            return

        if order.warehouse_orders.exists():
            raise WarehouseOrderNotEditableError(
                f"Inbound order '{order.code}' is read only once a warehouse order exists."
            )

        raise WarehouseOrderNotEditableError(
            f"Inbound order '{order.code}' is not editable in state '{InboundOrderState(order.state)}'."
        )

    @staticmethod
    def generate_next_incoming_order_code() -> str:
        return generate_next_sequential_code(
            queryset=InboundOrder.objects.all(), prefix="OV"
        )

    @staticmethod
    def generate_next_credit_note_code() -> str:
        now = timezone.now()
        dt_range = _get_month_range(now)
        notes_this_month = CreditNoteToSupplier.objects.filter(
            created__range=dt_range
        ).count()
        return f"DV{now.year}{now.month:02d}{notes_this_month + 1:04d}"

    @staticmethod
    def update_or_create_incoming(
        params: InboundOrderCreateOrUpdateSchema,
        context: RequestContext,
        code: str | None = None,
    ) -> InboundOrderSchema:
        if code is None:
            # todo: create code only after transitioning from 'draft'
            code = OrdersService.generate_next_incoming_order_code()

        previous_order_schema = None
        existing_order = InboundOrder.objects.filter(code=code).first()
        if existing_order:
            OrdersService._ensure_inbound_order_editable(existing_order)
            previous_order_schema = inbound_order_orm_to_schema(existing_order)

        supplier = Customer.objects.get(code=params.supplier_code)
        with transaction.atomic():
            order, created = InboundOrder.objects.update_or_create(
                code=code,
                defaults=dict(
                    external_code=params.external_code,
                    description=params.description,
                    note=params.note,
                    currency=params.currency,
                    supplier=supplier,
                    requested_delivery_date=params.requested_delivery_date,
                ),
            )
            if created:
                audit_service.add_entry(
                    order,
                    action=AuditAction.CREATE,
                    user=context.user_id,
                    reason=AuditMessages.NEW_INBOUND_ORDER_CREATED.CS,
                )
            else:
                if previous_order_schema:
                    new_order = inbound_order_orm_to_schema(order).model_dump()
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
                        reason=AuditMessages.WAREHOUSE_ORDER_UPDATED.CS,
                        changes=final_diff,
                    )

        return inbound_order_orm_to_schema(order)

    @staticmethod
    def add_item(
        code: str, item: InboundOrderItemCreateSchema
    ) -> InboundOrderItemSchema:
        order = InboundOrder.objects.get(code=code)
        OrdersService._ensure_inbound_order_editable(order)
        stock_product = StockProduct.objects.get(code=item.product_code)

        with transaction.atomic():
            InboundOrder.objects.select_for_update().get(pk=order.pk)
            next_index = order.items.count()
            amount = Decimal(str(item.amount))
            total_price = Decimal(str(item.total_price))
            item_model = InboundOrderItem.objects.create(
                stock_product=stock_product,
                amount=amount,
                order=order,
                total_price=total_price,
                unit_price=OrdersService._compute_unit_price(amount, total_price),
                index=item.index if item.index is not None else next_index,
                requires_certification=item.requires_certification,
            )

        return inbound_order_item_orm_to_schema(item_model)

    @staticmethod
    def update_item(
        code: str, item_index: int, item: InboundOrderItemCreateSchema
    ) -> InboundOrderItemSchema:
        order = InboundOrder.objects.get(code=code)
        OrdersService._ensure_inbound_order_editable(order)
        item_model = InboundOrderItem.objects.get(order=order, index=item_index)

        with transaction.atomic():
            amount = Decimal(str(item.amount))
            total_price = Decimal(str(item.total_price))
            item_model.amount = amount
            item_model.total_price = total_price
            item_model.unit_price = OrdersService._compute_unit_price(
                amount, total_price
            )
            if item.index is not None:
                item_model.index = item.index
            item_model.requires_certification = item.requires_certification
            item_model.save()
            if not item.requires_certification:
                # Unflagged row: drop the certificate link and its batch
                certifications_service.detach_from_inbound_item(item_model)

        return inbound_order_item_orm_to_schema(item_model)

    @staticmethod
    def remove_item(code: str, item_index: int) -> InboundOrderSchema:
        order = InboundOrder.objects.get(code=code)
        OrdersService._ensure_inbound_order_editable(order)
        item = InboundOrderItem.objects.get(order=order, index=item_index)
        with transaction.atomic():
            InboundOrder.objects.select_for_update().get(pk=order.pk)
            certifications_service.release_batch(item)
            item.delete()
            compact_order_items(order.items.select_for_update())

        order.refresh_from_db()
        return inbound_order_orm_to_schema(order)

    @staticmethod
    def reorder_item(code: str, item_index: int, new_index: int) -> InboundOrderSchema:
        order = InboundOrder.objects.get(code=code)
        OrdersService._ensure_inbound_order_editable(order)
        with transaction.atomic():
            reorder_order_items(order.items.select_for_update(), item_index, new_index)

        return inbound_order_orm_to_schema(order)

    @staticmethod
    def transition_order(
        code: str,
        context: RequestContext,
        action: str = "next",
        target_state: InboundOrderState | None = None,
    ) -> InboundOrderSchema:
        order = InboundOrder.objects.get(code=code)

        old_state = InboundOrderState(order.state)
        if target_state is None:
            if action == "cancel":
                # Prevent cancellation if warehouse orders have materialized items (fix bug #10)
                from apps.warehouse.models.warehouse import (
                    InboundWarehouseOrder,
                    InboundWarehouseOrderState,
                )

                warehouse_orders = InboundWarehouseOrder.objects.filter(order=order)
                for w_order in warehouse_orders:
                    if w_order.state in (
                        InboundWarehouseOrderState.PENDING,
                        InboundWarehouseOrderState.STARTED,
                        InboundWarehouseOrderState.COMPLETED,
                    ):
                        # Check if any warehouse items exist
                        if w_order.items.exists():
                            raise WarehouseItemBadRequestError(
                                f"Cannot cancel inbound order '{code}' - warehouse order '{w_order.code}' has materialized items. "
                                "Use credit note process to handle received items that need to be returned."
                            )
                new_state = InboundOrderState.CANCELLED
            elif action == "rollback":
                if old_state != InboundOrderState.PUTAWAY:
                    raise WarehouseItemBadRequestError(
                        f"Unsupported rollback from state '{old_state}'"
                    )
                new_state = InboundOrderState.RECEIVING
            elif action == "next":
                if old_state == InboundOrderState.DRAFT:
                    if not order.items.exists():
                        raise WarehouseItemBadRequestError(
                            "Order must have at least one item before confirmation"
                        )
                    missing = list(
                        order.items.filter(
                            requires_certification=True, certification__isnull=True
                        ).values_list("index", flat=True)
                    )
                    if missing:
                        rows = ", ".join(str(i + 1) for i in missing)
                        raise WarehouseItemBadRequestError(
                            f"Certification is required for item row(s): {rows}"
                        )
                    new_state = InboundOrderState.SUBMITTED
                elif old_state == InboundOrderState.SUBMITTED:
                    if not order.invoice:
                        raise WarehouseItemBadRequestError(
                            "Invoice must be attached before receiving transition"
                        )
                    new_state = InboundOrderState.RECEIVING
                elif old_state == InboundOrderState.RECEIVING:
                    new_state = InboundOrderState.PUTAWAY
                elif old_state == InboundOrderState.PUTAWAY:
                    new_state = InboundOrderState.COMPLETED
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

            if new_state == InboundOrderState.RECEIVING:
                order.received_date = timezone.now()

            if new_state == InboundOrderState.CANCELLED:
                order.cancelled_date = timezone.now()

            order.save()
            logger.info(
                f"Inboud order '{order.code}' transitioned: {old_state} -> {new_state}"
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

        return inbound_order_orm_to_schema(order)

    @staticmethod
    def transition_credit_note(
        code: str, new_state: CreditNoteState, context: RequestContext
    ) -> None:
        note = CreditNoteToSupplier.objects.get(code=code)
        with transaction.atomic():
            old_state = note.state
            note.state = new_state

            note.save()
            logger.info(
                f"Credit note '{note.code}' transitioned: {old_state} -> {new_state}"
            )
            audit_service.add_entry(
                note,
                user=context.user_id,
                action=AuditAction.TRANSITION,
                reason=AuditMessages.CREDIT_NOTE_STATE_CHANGED.CS.format(
                    old_state=old_state, new_state=new_state
                ),
                changes={"state": {"old": old_state, "new": new_state}},
            )

        return None

    @classmethod
    def accept_inbound_order(cls, order_code: str, context: RequestContext):
        # order = InboundOrder.objects.get(code=order_code)
        cls.transition_order(
            order_code,
            context=context,
            target_state=InboundOrderState.RECEIVING,
        )
        # for item in order.items.all():
        #     stock_product_service.update_pricing(item.stock_product.code)

    @staticmethod
    def get_html(code: str) -> str:
        order = InboundOrder.objects.get(code=code)
        order_schema = inbound_order_orm_to_schema(order)
        template = get_template("inbound_order.html")
        html_content = template.render({"order": order_schema.model_dump()})

        return html_content

    @classmethod
    def get_pdf(cls, code: str) -> bytes:
        return print_html_to_pdf(content_html=cls.get_html(code))

    @classmethod
    def get_or_create_credit_note(
        cls, order_code: str, context: RequestContext
    ) -> tuple[CreditNoteSupplierSchema, bool]:
        if not CreditNoteToSupplier.objects.filter(order__code=order_code).exists():
            order = InboundOrder.objects.get(code=order_code)
            created = True
            code = cls.generate_next_credit_note_code()
            note = CreditNoteToSupplier.objects.create(
                code=code, order=order, reason="", note="", state=CreditNoteState.DRAFT
            )

            result = credit_note_supplier_orm_to_schema(note)
            audit_service.add_entry(
                order,
                user=context.user_id,
                action=AuditAction.CREATE,
                reason=AuditMessages.CREDIT_NOTE_CREATED_FOR_INBOUND_ORDER.CS.format(
                    credit_note_code=note.code
                ),
                changes={"credit_note": {"created": note.code}},
            )
        else:
            order = InboundOrder.objects.get(code=order_code)
            created = False
            result = credit_note_supplier_orm_to_schema(order.credit_note)

        return result, created

    @classmethod
    def duplicate_inbound_order(
        cls, source_code: str, context: RequestContext
    ) -> InboundOrderSchema:
        source = InboundOrder.objects.prefetch_related("items__stock_product").get(
            code=source_code
        )
        new_code = cls.generate_next_incoming_order_code()

        with transaction.atomic():
            new_order = InboundOrder.objects.create(
                code=new_code,
                external_code=source.external_code,
                description=source.description,
                note=source.note,
                currency=source.currency,
                supplier=source.supplier,
                customer=source.customer,
                requested_delivery_date=source.requested_delivery_date,
                state=InboundOrderState.DRAFT,
            )
            for item in source.items.order_by("index"):
                InboundOrderItem.objects.create(
                    order=new_order,
                    stock_product=item.stock_product,
                    amount=item.amount,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                    index=item.index,
                    # certificate + batch are per delivery - to be supplied again
                    requires_certification=item.requires_certification,
                )
            audit_service.add_entry(
                new_order,
                action=AuditAction.CREATE,
                user=context.user_id,
                reason=AuditMessages.NEW_INBOUND_ORDER_CREATED.CS,
                changes={"duplicated_from": source_code},
            )

        return inbound_order_orm_to_schema(new_order)

    @classmethod
    def store_invoice(
        cls,
        order_code: str,
        params: InvoiceStoreSchema,
        context: RequestContext,
        invoice_file: UploadedFile | None = None,
    ) -> InboundOrderSchema:
        order = InboundOrder.objects.select_related("invoice").get(code=order_code)
        cls._ensure_inbound_order_editable(order)
        previous_invoice_code = order.invoice.code if order.invoice else None

        customer = cls._get_self_customer()
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

            if order.invoice_id != invoice.pk:
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
        return inbound_order_orm_to_schema(order)

    @classmethod
    def set_item_certification(
        cls,
        order_code: str,
        item_index: int,
        params: CertificationAttachSchema,
        attachment: UploadedFile | None = None,
    ) -> InboundOrderItemSchema:
        """Supply (or replace) the certification of a flagged order row."""
        order = InboundOrder.objects.get(code=order_code)
        cls._ensure_inbound_order_editable(order)
        item = InboundOrderItem.objects.select_related("order").get(
            order=order, index=item_index
        )
        certifications_service.attach_to_inbound_item(item, params, attachment)
        return inbound_order_item_orm_to_schema(item)

    @classmethod
    def remove_item_certification(
        cls, order_code: str, item_index: int
    ) -> InboundOrderItemSchema:
        order = InboundOrder.objects.get(code=order_code)
        cls._ensure_inbound_order_editable(order)
        item = InboundOrderItem.objects.get(order=order, index=item_index)
        certifications_service.detach_from_inbound_item(item)
        return inbound_order_item_orm_to_schema(item)


inbound_orders_service = OrdersService()
