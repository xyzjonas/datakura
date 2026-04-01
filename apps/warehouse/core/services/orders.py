from calendar import monthrange
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Q, QuerySet
from django.template.loader import get_template
from django.utils import timezone
from loguru import logger

from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
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
    ) -> QuerySet[InboundOrder]:
        qs = InboundOrder.objects.select_related(
            "supplier",
            "invoice__customer",
            "invoice__supplier",
            "invoice__payment_method",
        ).exclude(state__in=[InboundOrderState.CANCELLED, InboundOrderState.COMPLETED])

        if search_term:
            search_term = search_term.lower()
            qs = qs.filter(
                Q(code__iexact=search_term)
                | Q(code__icontains=search_term)
                | Q(supplier__name__icontains=search_term)
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
    def generate_next_incoming_order_code() -> str:
        now = timezone.now()
        dt_range = _get_month_range(now)
        orders_this_month = InboundOrder.objects.filter(created__range=dt_range).count()
        return f"OV{now.year}{now.month:02d}{orders_this_month + 1:04d}"

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
        stock_product = StockProduct.objects.get(code=item.product_code)

        if InboundOrderItem.objects.filter(
            order=order, stock_product=stock_product
        ).exists():
            raise WarehouseItemBadRequestError(
                f"Item for product '{stock_product.code}' already exists in order '{order.code}'"
            )

        with transaction.atomic():
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
            )

        return inbound_order_item_orm_to_schema(item_model)

    @staticmethod
    def update_item(
        code: str, item: InboundOrderItemCreateSchema
    ) -> InboundOrderItemSchema:
        order = InboundOrder.objects.get(code=code)
        item_model = InboundOrderItem.objects.get(
            order=order, stock_product__code=item.product_code
        )

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
            item_model.save()

        return inbound_order_item_orm_to_schema(item_model)

    @staticmethod
    def remove_item(code: str, product_code: str) -> bool:
        order = InboundOrder.objects.get(code=code)
        items = InboundOrderItem.objects.filter(
            order=order, stock_product__code=product_code
        )
        with transaction.atomic():
            items.delete()

        return True

    @staticmethod
    def transition_order(
        code: str, new_state: InboundOrderState, context: RequestContext
    ) -> InboundOrderSchema:
        order = InboundOrder.objects.get(code=code)
        with transaction.atomic():
            old_state = order.state
            order.state = new_state

            if new_state == InboundOrderState.RECEIVING:
                order.received_date = timezone.now()

            if order.state == InboundOrderState.CANCELLED:
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
        cls.transition_order(order_code, InboundOrderState.RECEIVING, context=context)
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
    def store_invoice(
        cls,
        order_code: str,
        params: InvoiceStoreSchema,
        context: RequestContext,
        invoice_file: UploadedFile | None = None,
    ) -> InboundOrderSchema:
        order = InboundOrder.objects.select_related("invoice").get(code=order_code)
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


inbound_orders_service = OrdersService()
