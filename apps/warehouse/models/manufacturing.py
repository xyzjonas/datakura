from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.db.models import QuerySet

from .base import BaseModel
from .customer import Customer
from .product import StockProduct

if TYPE_CHECKING:
    from .warehouse import InboundWarehouseOrder, OutboundWarehouseOrder


class ManufacturingOrderState(models.IntegerChoices):
    DRAFT = 1, "Draft"
    CONFIRMED = 2, "Confirmed"
    IN_PROGRESS = 3, "In Progress"
    COMPLETED = 4, "Completed"
    CANCELLED = 5, "Cancelled"

    @classmethod
    def get_label(cls, value):
        member = value if isinstance(value, cls) else cls(value)
        api_values = {
            cls.DRAFT: "draft",
            cls.CONFIRMED: "confirmed",
            cls.IN_PROGRESS: "in_progress",
            cls.COMPLETED: "completed",
            cls.CANCELLED: "cancelled",
        }
        return api_values.get(member, str(value))


class ManufacturingOrder(BaseModel):
    """Manufacturing / production order - items dispatched to a customer and returned refined."""

    code = models.CharField(max_length=50, unique=True, null=False)
    description = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    state = models.PositiveIntegerField(
        choices=ManufacturingOrderState.choices,
        default=ManufacturingOrderState.DRAFT,
    )
    is_external = models.BooleanField(
        default=False,
        help_text="Whether the work is done by an external contractor",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="manufacturing_orders_as_customer",
        help_text="Internal department or external contractor performing the work",
        default=Customer.get_ghost_customer,
    )
    supplier = models.ForeignKey(
        Customer,
        on_delete=models.SET_DEFAULT,
        related_name="manufacturing_orders_as_supplier",
        help_text="Supplier performing the manufacturing service",
        default=Customer.get_ghost_customer,
    )
    cancelled_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)

    items: QuerySet["ManufacturingOrderItem"]
    outbound_warehouse_orders: "QuerySet[OutboundWarehouseOrder]"
    inbound_warehouse_orders: "QuerySet[InboundWarehouseOrder]"

    class Meta(BaseModel.Meta):
        ordering = ["-created"]

    def __str__(self) -> str:
        return self.code


class ManufacturingOrderItem(BaseModel):
    """A single IN→OUT pair: an input product is consumed and output product is produced."""

    order = models.ForeignKey(
        ManufacturingOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    in_product = models.ForeignKey(
        StockProduct,
        on_delete=models.PROTECT,
        related_name="mfg_order_in_items",
        help_text="Product sent to the customer (consumed)",
    )
    in_amount = models.DecimalField(max_digits=10, decimal_places=4)
    out_product = models.ForeignKey(
        StockProduct,
        on_delete=models.PROTECT,
        related_name="mfg_order_out_items",
        help_text="Product returned from the customer (produced)",
    )
    out_amount = models.DecimalField(max_digits=10, decimal_places=4)
    index = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["index", "created"]

    def __str__(self) -> str:
        return (
            f"{self.in_amount}× {self.in_product.name}"
            f" → {self.out_amount}× {self.out_product.name}"
        )
