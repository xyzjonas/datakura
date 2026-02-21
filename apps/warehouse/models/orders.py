from __future__ import annotations
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import QuerySet
from django.db.models.fields.related import ForeignKey

from .base import BaseModel
from .currency import CURRENCY_CHOICES
from .customer import Customer
from .product import StockProduct

if TYPE_CHECKING:
    from .warehouse import InboundWarehouseOrder


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


class CreditNoteState(models.TextChoices):
    DRAFT = "draft", "Draft"
    CONFIRMED = "confirmed", "Confirmed"


class InboundOrder(BaseModel):
    """Incoming order, or "purchase" order"""

    code = models.CharField(max_length=50, null=False, unique=True)
    external_code = models.CharField(
        max_length=50, null=True, blank=True
    )  # todo: add unique constraint
    description = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    supplier = models.ForeignKey(Customer, null=False, on_delete=models.PROTECT)
    items: QuerySet["InboundOrderItem"]

    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CZK")
    state = models.CharField(
        max_length=20,
        choices=InboundOrderState.choices,
        default=InboundOrderState.DRAFT,
    )

    warehouse_order: InboundWarehouseOrder | None
    credit_note: "CreditNoteToSupplier"

    requested_delivery_date = models.DateTimeField(null=True, blank=True)
    cancelled_date = models.DateTimeField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"{self.code} | {self.supplier.name}"

    @property
    def warehouse_order_code(self) -> str | None:
        if hasattr(self, "warehouse_order") and self.warehouse_order:
            return self.warehouse_order.code
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
    unit_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)

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
    unit_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    def __str__(self):
        return f"{self.amount} × {self.stock_product.name}"
