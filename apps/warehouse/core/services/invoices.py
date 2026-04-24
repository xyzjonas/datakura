from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import QuerySet
from django.template.loader import get_template
from django.utils import timezone

from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.exceptions import (
    NotFoundException,
    WarehouseItemBadRequestError,
)
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.invoice import (
    InvoiceDetailSchema,
    InvoiceStoreSchema,
    OutboundInvoiceCreateSchema,
)
from apps.warehouse.core.services import audit_service
from apps.warehouse.core.services.pdf import print_html_to_pdf
from apps.warehouse.core.transformation import invoice_orm_to_detail_schema
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.orders import (
    Invoice,
    InvoicePaymentMethod,
    OutboundOrder,
    OutboundOrderState,
)
from apps.warehouse.models.warehouse import OutboundWarehouseOrderState


def _get_end_of_month(date: datetime) -> datetime:
    last_day = monthrange(date.year, date.month)[1]
    return date.replace(day=last_day)


def _get_month_range(date: datetime) -> tuple[datetime, datetime]:
    last_day = _get_end_of_month(date)
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0), last_day


class InvoicesService:
    @staticmethod
    def _build_invoice_changes(
        invoice: Invoice,
        *,
        customer: Customer | None,
        supplier: Customer | None,
        payment_method: InvoicePaymentMethod,
        code: str,
        issued_date: date,
        due_date: date,
        external_code: str | None,
        taxable_supply_date: date,
        paid_date: date | None,
        currency: str,
        note: str | None,
        invoice_file_name: str | None = None,
    ) -> dict[str, dict[str, str | None]]:
        changes: dict[str, dict[str, str | None]] = {}
        tracked_fields = {
            "customer": (
                invoice.customer.code if invoice.customer else None,
                customer.code if customer else None,
            ),
            "supplier": (
                invoice.supplier.code if invoice.supplier else None,
                supplier.code if supplier else None,
            ),
            "code": (invoice.code, code),
            "issued_date": (
                invoice.issued_date.isoformat() if invoice.issued_date else None,
                issued_date.isoformat(),
            ),
            "due_date": (
                invoice.due_date.isoformat() if invoice.due_date else None,
                due_date.isoformat(),
            ),
            "payment_method": (invoice.payment_method.name, payment_method.name),
            "external_code": (invoice.external_code, external_code),
            "taxable_supply_date": (
                invoice.taxable_supply_date.isoformat()
                if invoice.taxable_supply_date
                else None,
                taxable_supply_date.isoformat(),
            ),
            "paid_date": (
                invoice.paid_date.isoformat() if invoice.paid_date else None,
                paid_date.isoformat() if paid_date else None,
            ),
            "currency": (invoice.currency, currency),
            "note": (invoice.note, note),
        }

        if invoice_file_name is not None:
            tracked_fields["document"] = (
                invoice.document.name if invoice.document else None,
                invoice_file_name,
            )

        for field, (old_value, new_value) in tracked_fields.items():
            if old_value != new_value:
                changes[field] = {"old": old_value, "new": new_value}

        return changes

    @staticmethod
    def _get_related_outbound_orders(invoice: Invoice) -> list[OutboundOrder]:
        return list(
            invoice.outbound_orders.select_related("invoice").prefetch_related(
                "warehouse_orders"
            )
        )

    @staticmethod
    def _get_invoice_queryset() -> QuerySet[Invoice]:
        return Invoice.objects.select_related(
            "customer",
            "supplier",
            "payment_method",
        ).prefetch_related(
            "inbound_orders__items__stock_product__unit_of_measure",
            "outbound_orders__items__stock_product__unit_of_measure",
        )

    @staticmethod
    def _get_related_orders(invoice: InvoiceDetailSchema):
        return invoice.outbound_orders or invoice.inbound_orders

    @classmethod
    def get_outbound_invoices(cls) -> QuerySet[Invoice]:
        return (
            cls._get_invoice_queryset()
            .filter(outbound_orders__isnull=False)
            .distinct()
            .order_by("-created")
        )

    @classmethod
    def get_inbound_invoices(cls) -> QuerySet[Invoice]:
        return (
            cls._get_invoice_queryset()
            .filter(inbound_orders__isnull=False)
            .distinct()
            .order_by("-created")
        )

    @staticmethod
    def _has_completed_warehouse_order(order: OutboundOrder) -> bool:
        warehouse_orders = list(order.warehouse_orders.all())
        return bool(warehouse_orders) and all(
            warehouse_order.state == OutboundWarehouseOrderState.COMPLETED
            for warehouse_order in warehouse_orders
        )

    @staticmethod
    def _get_self_customer() -> Customer:
        try:
            return Customer.objects.get(is_self=True, is_deleted=False)
        except Customer.DoesNotExist as exc:
            raise WarehouseItemBadRequestError(
                "Set exactly one active customer as self before creating outbound invoices."
            ) from exc

    @staticmethod
    def _resolve_payment_method(
        customer: Customer,
        payment_method_name: str | None,
    ) -> InvoicePaymentMethod:
        normalized_name = (payment_method_name or "").strip()
        if normalized_name:
            return InvoicePaymentMethod.objects.get_or_create(name=normalized_name)[0]

        if customer.default_payment_method_id:
            default_payment_method = customer.default_payment_method
            if default_payment_method is not None:
                return default_payment_method

        raise WarehouseItemBadRequestError(
            "Customer does not have a default payment method configured."
        )

    @staticmethod
    def _ordered_unique_codes(order_codes: list[str]) -> list[str]:
        return list(dict.fromkeys(order_codes))

    @staticmethod
    def generate_next_outbound_invoice_code() -> str:
        now = timezone.now()
        dt_range = _get_month_range(now)
        prefix = f"SINV{now.year}{now.month:02d}"
        sequence = (
            Invoice.objects.filter(
                created__range=dt_range, code__startswith=prefix
            ).count()
            + 1
        )

        while True:
            code = f"{prefix}{sequence:04d}"
            if not Invoice.objects.filter(code=code).exists():
                return code
            sequence += 1

    @classmethod
    def get_invoice(cls, invoice_code: str) -> InvoiceDetailSchema:
        invoice = cls._get_invoice_queryset().get(code=invoice_code)
        return invoice_orm_to_detail_schema(invoice)

    @classmethod
    def get_html(cls, invoice_code: str) -> str:
        invoice = cls.get_invoice(invoice_code)
        order_sections = []
        total_amount = Decimal("0")
        for order in cls._get_related_orders(invoice):
            order_total_amount = sum(
                (Decimal(str(item.total_price)) for item in order.items),
                Decimal("0"),
            )
            total_amount += order_total_amount
            order_sections.append(
                {
                    "order": order.model_dump(),
                    "total_amount": order_total_amount,
                }
            )
        template = get_template("outbound_invoice.html")
        return template.render(
            {
                "invoice": invoice.model_dump(),
                "order_sections": order_sections,
                "total_amount": total_amount,
            }
        )

    @classmethod
    def get_pdf(cls, invoice_code: str) -> bytes:
        return print_html_to_pdf(content_html=cls.get_html(invoice_code))

    @classmethod
    def create_outbound_invoice(
        cls,
        params: OutboundInvoiceCreateSchema,
        context: RequestContext,
    ) -> InvoiceDetailSchema:
        from apps.warehouse.core.services.outbound_orders import outbound_orders_service

        order_codes = cls._ordered_unique_codes(params.order_codes)
        if not order_codes:
            raise WarehouseItemBadRequestError(
                "Select at least one outbound order for invoicing."
            )

        orders = list(
            OutboundOrder.objects.select_related("customer", "invoice")
            .prefetch_related(
                "items__stock_product__unit_of_measure",
                "warehouse_orders",
            )
            .filter(code__in=order_codes)
        )
        orders_by_code = {order.code: order for order in orders}
        missing_codes = [code for code in order_codes if code not in orders_by_code]
        if missing_codes:
            raise NotFoundException(
                f"Outbound orders not found: {', '.join(missing_codes)}"
            )

        ordered_orders = [orders_by_code[code] for code in order_codes]

        invalid_states = [
            order.code
            for order in ordered_orders
            if order.state in (OutboundOrderState.DRAFT, OutboundOrderState.CANCELLED)
        ]
        if invalid_states:
            raise WarehouseItemBadRequestError(
                "Only confirmed outbound orders can be invoiced: "
                + ", ".join(invalid_states)
            )

        orders_without_completed_warehouse = [
            order.code
            for order in ordered_orders
            if not cls._has_completed_warehouse_order(order)
        ]
        if orders_without_completed_warehouse:
            raise WarehouseItemBadRequestError(
                "Only outbound orders with completed warehouse orders can be invoiced: "
                + ", ".join(orders_without_completed_warehouse)
            )

        already_invoiced = [
            order.code for order in ordered_orders if order.invoice_id is not None
        ]
        if already_invoiced:
            raise WarehouseItemBadRequestError(
                "Some outbound orders already have an invoice: "
                + ", ".join(already_invoiced)
            )

        customer_ids = {order.customer_id for order in ordered_orders}
        if len(customer_ids) != 1:
            raise WarehouseItemBadRequestError(
                "Selected outbound orders must belong to same customer."
            )

        currencies = {order.currency for order in ordered_orders}
        if len(currencies) != 1:
            raise WarehouseItemBadRequestError(
                "Selected outbound orders must use same currency."
            )

        customer = ordered_orders[0].customer
        supplier = cls._get_self_customer()
        payment_method = cls._resolve_payment_method(
            customer, params.payment_method_name
        )
        invoice_code = cls.generate_next_outbound_invoice_code()
        currency = ordered_orders[0].currency

        with transaction.atomic():
            invoice = Invoice.objects.create(
                customer=customer,
                supplier=supplier,
                code=invoice_code,
                issued_date=params.issued_date,
                due_date=params.due_date,
                payment_method=payment_method,
                external_code=params.external_code,
                taxable_supply_date=params.taxable_supply_date,
                paid_date=params.paid_date,
                currency=currency,
                note=params.note,
            )

            for order in ordered_orders:
                order.invoice = invoice
                order.save()
                audit_service.add_entry(
                    order,
                    user=context.user_id,
                    action=AuditAction.UPDATE,
                    reason=AuditMessages.INVOICE_CREATED_FOR_OUTBOUND_ORDER.CS.format(
                        invoice_code=invoice.code
                    ),
                    changes={
                        "invoice": {
                            "old": None,
                            "new": invoice.code,
                        }
                    },
                )
                outbound_orders_service.sync_state_from_invoice(order, context)

        created_invoice = cls._get_invoice_queryset().get(pk=invoice.pk)
        return invoice_orm_to_detail_schema(created_invoice)

    @classmethod
    def update_invoice(
        cls,
        invoice_code: str,
        params: InvoiceStoreSchema,
        context: RequestContext,
        invoice_file=None,
    ) -> InvoiceDetailSchema:
        from apps.warehouse.core.services.outbound_orders import outbound_orders_service

        invoice = cls._get_invoice_queryset().get(code=invoice_code)
        customer = (
            Customer.objects.get(code=params.customer_code)
            if params.customer_code
            else None
        )
        supplier = (
            Customer.objects.get(code=params.supplier_code)
            if params.supplier_code
            else None
        )
        payment_method, _ = InvoicePaymentMethod.objects.get_or_create(
            name=params.payment_method_name
        )
        changes = cls._build_invoice_changes(
            invoice,
            customer=customer,
            supplier=supplier,
            payment_method=payment_method,
            code=params.code,
            issued_date=params.issued_date,
            due_date=params.due_date,
            external_code=params.external_code,
            taxable_supply_date=params.taxable_supply_date,
            paid_date=params.paid_date,
            currency=params.currency,
            note=params.note,
            invoice_file_name=invoice_file.name if invoice_file is not None else None,
        )

        with transaction.atomic():
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
                if invoice.document:
                    invoice.document.delete(save=False)
                invoice.document = invoice_file

            invoice.save()

            if changes:
                audit_service.add_entry(
                    invoice,
                    user=context.user_id,
                    action=AuditAction.UPDATE,
                    reason=AuditMessages.INVOICE_UPDATED.CS,
                    changes=changes,
                )

            for order in cls._get_related_outbound_orders(invoice):
                outbound_orders_service.sync_state_from_invoice(order, context)

        updated_invoice = cls._get_invoice_queryset().get(pk=invoice.pk)
        return invoice_orm_to_detail_schema(updated_invoice)

    @classmethod
    def mark_invoice_paid(
        cls,
        invoice_code: str,
        context: RequestContext,
        paid_date: date | None = None,
    ) -> InvoiceDetailSchema:
        from apps.warehouse.core.services.outbound_orders import outbound_orders_service

        invoice = cls._get_invoice_queryset().get(code=invoice_code)
        resolved_paid_date = paid_date or timezone.localdate()
        old_paid_date = invoice.paid_date.isoformat() if invoice.paid_date else None

        with transaction.atomic():
            invoice.paid_date = resolved_paid_date
            invoice.save(update_fields=["paid_date", "changed"])

            audit_service.add_entry(
                invoice,
                user=context.user_id,
                action=AuditAction.UPDATE,
                reason=AuditMessages.INVOICE_MARKED_AS_PAID.CS,
                changes={
                    "paid_date": {
                        "old": old_paid_date,
                        "new": resolved_paid_date.isoformat(),
                    }
                },
            )

            for order in cls._get_related_outbound_orders(invoice):
                outbound_orders_service.sync_state_from_invoice(order, context)

        paid_invoice = cls._get_invoice_queryset().get(pk=invoice.pk)
        return invoice_orm_to_detail_schema(paid_invoice)


invoice_service = InvoicesService()
