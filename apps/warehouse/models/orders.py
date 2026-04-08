from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING

from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import QuerySet
from django.db.models.fields.related import ForeignKey

from .base import BaseModel
from .currency import CURRENCY_CHOICES
from .customer import Customer
from .product import StockProduct

if TYPE_CHECKING:
    from .warehouse import InboundWarehouseOrder  # noqa: F401
    from .warehouse import OutboundWarehouseOrder  # noqa: F401


def invoice_document_upload_to(instance: Invoice, filename: str) -> str:
    return f"invoices/{instance.code}/{filename}"


class InboundOrderState(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    # IN_TRANSIT = "in_transit", "In Transit"
    # ARRIVED = "arrived", "Arrived"
    RECEIVING = "receiving", "Receiving"
    # QUALITY_CHECK = "quality_check", "Quality Check"
    PUTAWAY = "putaway", "Put Away"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    # PARTIALLY_RECEIVED = "partially_received", "Partially Received"


class OutboundOrderState(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    PICKING = "picking", "Picking"
    PACKING = "packing", "Packing"
    SHIPPING = "shipping", "Shipping"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class CreditNoteState(models.TextChoices):
    DRAFT = "draft", "Draft"
    CONFIRMED = "confirmed", "Confirmed"


class InvoicePaymentMethod(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta(BaseModel.Meta):
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Invoice(BaseModel):
    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="customer_invoices",
    )
    supplier = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="supplier_invoices",
    )
    code = models.CharField(max_length=50, null=False, unique=True)
    issued_date = models.DateField()
    due_date = models.DateField()
    payment_method = models.ForeignKey(
        InvoicePaymentMethod,
        null=False,
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    external_code = models.CharField(max_length=50, null=True, blank=True)
    taxable_supply_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CZK")
    note = models.TextField(null=True, blank=True)
    document = models.FileField(
        upload_to=invoice_document_upload_to,
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )

    class Meta(BaseModel.Meta):
        ordering = ["-issued_date", "-created"]

    def __str__(self) -> str:
        return self.code


class InboundOrder(BaseModel):
    """Incoming order, or "purchase" order"""

    code = models.CharField(max_length=50, null=False, unique=True)
    external_code = models.CharField(
        max_length=50, null=True, blank=True
    )  # todo: add unique constraint
    description = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    invoice = models.ForeignKey(
        Invoice,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inbound_orders",
    )

    supplier = models.ForeignKey(Customer, null=False, on_delete=models.PROTECT)
    items: QuerySet["InboundOrderItem"]

    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CZK")
    state = models.CharField(
        max_length=20,
        choices=InboundOrderState.choices,
        default=InboundOrderState.DRAFT,
    )

    warehouse_orders: "QuerySet[InboundWarehouseOrder]"
    credit_note: "CreditNoteToSupplier"

    requested_delivery_date = models.DateTimeField(null=True, blank=True)
    cancelled_date = models.DateTimeField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"{self.code} | {self.supplier.name}"

    @property
    def warehouse_order_code(self) -> str | None:
        warehouse_order = getattr(self, "warehouse_order", None)
        if warehouse_order:
            return warehouse_order.code
        return None


class InboundOrderItem(BaseModel):
    """Incoming order"""

    stock_product = models.ForeignKey(
        StockProduct, null=False, on_delete=models.PROTECT
    )
    amount = models.DecimalField(max_digits=10, decimal_places=4, null=False)
    order = models.ForeignKey(
        InboundOrder,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="items",
    )
    index = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal("0")
    )
    total_price = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal("0")
    )

    class Meta(BaseModel.Meta):
        ordering = ["index", "created"]

    def __str__(self):
        return f"{self.amount} × {self.stock_product.name}"


class OutboundOrder(BaseModel):
    """Outgoing order, or "sales" order"""

    code = models.CharField(max_length=50, null=False, unique=True)
    external_code = models.CharField(
        max_length=50, null=True, blank=True
    )  # todo: add unique constraint
    description = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    invoice = models.ForeignKey(
        Invoice,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="outbound_orders",
    )

    customer = models.ForeignKey(Customer, null=False, on_delete=models.PROTECT)
    items: QuerySet["OutboundOrderItem"]

    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CZK")
    state = models.CharField(
        max_length=20,
        choices=OutboundOrderState.choices,
        default=OutboundOrderState.DRAFT,
    )

    warehouse_orders: "QuerySet[OutboundWarehouseOrder]"
    credit_note: "CreditNoteToCustomer"

    requested_delivery_date = models.DateTimeField(null=True, blank=True)
    cancelled_date = models.DateTimeField(null=True, blank=True)
    fulfilled_date = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"{self.code} | {self.customer.name}"


class OutboundOrderItem(BaseModel):
    """Outgoing order item"""

    stock_product = models.ForeignKey(
        StockProduct, null=False, on_delete=models.PROTECT
    )
    amount = models.DecimalField(max_digits=10, decimal_places=4, null=False)
    order = models.ForeignKey(
        OutboundOrder,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="items",
    )
    index = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal("0")
    )
    total_price = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal("0")
    )

    class Meta(BaseModel.Meta):
        ordering = ["index", "created"]

    def __str__(self):
        return f"{self.amount} × {self.stock_product.name}"


class CreditNoteToSupplier(BaseModel):
    """Credit note"""

    code = models.CharField(max_length=50, null=False, unique=True)
    order = models.OneToOneField(
        InboundOrder, on_delete=models.CASCADE, related_name="credit_note"
    )
    reason = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    state = models.CharField(
        max_length=20,
        choices=CreditNoteState.choices,
        default=CreditNoteState.DRAFT,
    )

    items: QuerySet["CreditNoteToSupplierItem"]


class CreditNoteToSupplierItem(BaseModel):
    """Credit note item (returning back to suppliers)"""

    stock_product = models.ForeignKey(
        StockProduct, null=False, on_delete=models.PROTECT
    )
    amount = models.DecimalField(max_digits=10, decimal_places=4, null=False)
    credit_note = ForeignKey(
        CreditNoteToSupplier,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="items",
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal("0")
    )

    def __str__(self):
        return f"{self.amount} × {self.stock_product.name}"


class CreditNoteToCustomer(BaseModel):
    """Credit note"""

    code = models.CharField(max_length=50, null=False, unique=True)
    order = models.OneToOneField(
        OutboundOrder, on_delete=models.CASCADE, related_name="credit_note"
    )
    reason = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    state = models.CharField(
        max_length=20,
        choices=CreditNoteState.choices,
        default=CreditNoteState.DRAFT,
    )

    items: QuerySet["CreditNoteToCustomerItem"]


class CreditNoteToCustomerItem(BaseModel):
    """Credit note item (crediting customer)"""

    stock_product = models.ForeignKey(
        StockProduct, null=False, on_delete=models.PROTECT
    )
    amount = models.DecimalField(max_digits=10, decimal_places=4, null=False)
    credit_note = ForeignKey(
        CreditNoteToCustomer,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="items",
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal("0")
    )

    def __str__(self):
        return f"{self.amount} × {self.stock_product.name}"
