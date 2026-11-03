from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING

from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import QuerySet
from django.db.models.fields.related import ForeignKey

from .base import BaseModel
from .currency import CURRENCY_CHOICES
from .customer import ContactPerson, Customer
from .packaging import PackageType
from .product import StockProduct

if TYPE_CHECKING:
    from .warehouse import InboundWarehouseOrder  # noqa: F401
    from .warehouse import OutboundWarehouseOrder  # noqa: F401


def invoice_document_upload_to(instance: Invoice, filename: str) -> str:
    return f"invoices/{instance.code}/{filename}"


class InboundOrderState(models.IntegerChoices):
    DRAFT = 1, "Draft"
    SUBMITTED = 2, "Submitted"
    RECEIVING = 3, "Receiving"
    PUTAWAY = 4, "Put Away"
    COMPLETED = 5, "Completed"
    CANCELLED = 6, "Cancelled"

    @classmethod
    def get_label(cls, value):
        """Return the API string for a given state value."""
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError, TypeError:
                pass
        member = value if isinstance(value, cls) else cls(value)
        api_values = {
            cls.DRAFT: "draft",
            cls.SUBMITTED: "submitted",
            cls.RECEIVING: "receiving",
            cls.PUTAWAY: "putaway",
            cls.COMPLETED: "completed",
            cls.CANCELLED: "cancelled",
        }
        if member in api_values:
            return api_values[member]
        return str(value)


class OutboundOrderState(models.IntegerChoices):
    # value 1 (the former "Calculation" draft) is retired: calculations live in
    # their own tables, an order starts as SUBMITTED ("Potvrzeno")
    SUBMITTED = 2, "Submitted"
    PICKING = 3, "Picking"
    PACKING = 4, "Packing"
    SHIPPING = 5, "Shipping"
    COMPLETED = 6, "Completed"
    CANCELLED = 7, "Cancelled"
    SENT = 8, "Sent"
    INVOICED = 9, "Invoiced"
    WAITING_FOR_PAYMENT = 10, "Waiting for payment"
    COMPLETED_PAID = 11, "Completed paid"

    @classmethod
    def get_label(cls, value):
        """Return the API string for a given state value."""
        member = value if isinstance(value, cls) else cls(value)
        api_values = {
            cls.SUBMITTED: "submitted",
            cls.PICKING: "picking",
            cls.PACKING: "packing",
            cls.SHIPPING: "shipping",
            cls.COMPLETED: "completed",
            cls.CANCELLED: "cancelled",
            cls.SENT: "sent",
            cls.INVOICED: "invoiced",
            cls.WAITING_FOR_PAYMENT: "waiting_for_payment",
            cls.COMPLETED_PAID: "completed_paid",
        }
        if member in api_values:
            return api_values[member]
        return str(value)


class OutboundCalculationState(models.IntegerChoices):
    OPEN = 1, "Open"
    CLOSED = 2, "Closed"

    @classmethod
    def get_label(cls, value):
        """Return the API string for a given state value."""
        return {cls.OPEN: "open", cls.CLOSED: "closed"}[cls(value)]


class CreditNoteState(models.IntegerChoices):
    DRAFT = 1, "Draft"
    CONFIRMED = 2, "Confirmed"

    @classmethod
    def get_label(cls, value):
        """Return the API string for a given state value."""
        member = value if isinstance(value, cls) else cls(value)
        api_values = {
            cls.DRAFT: "draft",
            cls.CONFIRMED: "confirmed",
        }
        if member in api_values:
            return api_values[member]
        return str(value)


class InvoicePaymentMethod(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta(BaseModel.Meta):
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @classmethod
    def resolve(cls, name: str | None) -> "InvoicePaymentMethod | None":
        """Get or create a payment method by name; blank name means none."""
        normalized_name = (name or "").strip()
        if not normalized_name:
            return None
        return cls.objects.get_or_create(name=normalized_name)[0]


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
    issued_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    payment_method = models.ForeignKey(
        InvoicePaymentMethod,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    external_code = models.CharField(max_length=50, null=True, blank=True)
    taxable_supply_date = models.DateField(null=True, blank=True)
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
    """
    PURCHASE order: WE buy goods FROM a supplier (CZ UI: "Vydané objednávky" -
    orders *issued* by us). Goods come IN to our warehouse, hence "inbound":
    receiving/put-away happens via `InboundWarehouseOrder` (příjemka).

    - `supplier` is the party we buy from (`customer` is us, the ghost/self customer).
    - Not to be confused with `OutboundOrder`, the sales order a client places with us.
    - Single table, no calculation (draft) concept: drafts are listed together
      with the other states.
    """

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
    customer = models.ForeignKey(
        Customer,
        null=False,
        on_delete=models.SET_DEFAULT,
        related_name="inbound_orders_as_customer",
        default=Customer.get_ghost_customer,
    )
    supplier = models.ForeignKey(
        Customer,
        null=False,
        on_delete=models.SET_DEFAULT,
        related_name="inbound_orders_as_supplier",
        default=Customer.get_ghost_customer,
    )
    items: QuerySet["InboundOrderItem"]

    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CZK")
    state = models.PositiveIntegerField(
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
        constraints = [
            models.UniqueConstraint(
                fields=["order", "index"], name="unique_inbound_order_item_order_index"
            )
        ]

    def __str__(self):
        return f"{self.amount} × {self.stock_product.name}"


class OutboundOrder(BaseModel):
    """
    SALES order: a CLIENT buys goods FROM us (CZ UI: "Přijaté objednávky" -
    orders *received* by us). Goods go OUT of our warehouse, hence "outbound":
    picking/shipping happens via `OutboundWarehouseOrder` (výdejka).

    - `customer` is the buyer (`supplier` is us, the ghost/self customer).
    - Not to be confused with `InboundOrder`, the purchase order we place with a supplier.
    - Starts as SUBMITTED, either created directly or mirrored 1:1 from an
      `OutboundCalculation` (`OutboundCalculation.order`). Confirming it
      (transition to PICKING) creates the warehouse order.
    """

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

    supplier = models.ForeignKey(
        Customer,
        null=False,
        on_delete=models.SET_DEFAULT,
        related_name="outbound_orders_as_customer",
        default=Customer.get_ghost_customer,
    )
    customer = models.ForeignKey(
        Customer,
        null=False,
        on_delete=models.SET_DEFAULT,
        related_name="outbound_orders_as_supplier",
        default=Customer.get_ghost_customer,
    )
    # Where to ship / whom to invoice within `customer` (e.g. one of many shops).
    # Always a contact of `customer`; null = not specified.
    contact = models.ForeignKey(
        ContactPerson,
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="outbound_orders",
    )
    items: QuerySet["OutboundOrderItem"]

    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CZK")
    state = models.PositiveIntegerField(
        choices=OutboundOrderState.choices,
        default=OutboundOrderState.SUBMITTED,
    )

    warehouse_orders: "QuerySet[OutboundWarehouseOrder]"
    credit_note: "CreditNoteToCustomer"
    calculation: "OutboundCalculation | None"

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
    desired_package_type = models.ForeignKey(
        PackageType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="outbound_order_items",
    )
    desired_batch = models.ForeignKey(
        "warehouse.Batch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="outbound_order_items",
    )
    note = models.TextField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["index", "created"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "index"], name="unique_outbound_order_item_order_index"
            )
        ]

    def __str__(self):
        return f"{self.amount} × {self.stock_product.name}"


class OutboundCalculationQuerySet(models.QuerySet["OutboundCalculation"]):
    def active(self) -> "OutboundCalculationQuerySet":
        """Calculations that were not (soft) deleted."""
        return self.filter(is_deleted=False)


class OutboundCalculation(BaseModel):
    """
    Offer for a client (the pre-stage of an `OutboundOrder`, i.e. a sales order).

    Mirrors the header of `OutboundOrder` but has its own tables and only two
    states (open/closed) and no warehouse/invoice side. Once the buyer confirms the
    deal it is flipped over to an order (`order`), which is an independent 1:1 copy:
    the calculation stays untouched (just closed).

    Deleting is soft (`is_deleted`), so calculations are never lost.
    """

    code = models.CharField(max_length=50, null=False, unique=True)
    external_code = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    supplier = models.ForeignKey(
        Customer,
        null=False,
        on_delete=models.SET_DEFAULT,
        related_name="outbound_calculations_as_customer",
        default=Customer.get_ghost_customer,
    )
    customer = models.ForeignKey(
        Customer,
        null=False,
        on_delete=models.SET_DEFAULT,
        related_name="outbound_calculations_as_supplier",
        default=Customer.get_ghost_customer,
    )
    contact = models.ForeignKey(
        ContactPerson,
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="outbound_calculations",
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CZK")
    state = models.PositiveIntegerField(
        choices=OutboundCalculationState.choices,
        default=OutboundCalculationState.OPEN,
    )
    requested_delivery_date = models.DateTimeField(null=True, blank=True)

    # the order created from this calculation (null = not flipped over yet)
    order = models.OneToOneField(
        OutboundOrder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="calculation",
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_date = models.DateTimeField(null=True, blank=True)

    items: QuerySet["OutboundCalculationItem"]
    objects = OutboundCalculationQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        ordering = ["-created"]

    def __str__(self) -> str:
        return f"{self.code} | {self.customer.name}"


class OutboundCalculationItem(BaseModel):
    """Calculation item, field-for-field the same as `OutboundOrderItem`."""

    stock_product = models.ForeignKey(
        StockProduct, null=False, on_delete=models.PROTECT
    )
    amount = models.DecimalField(max_digits=10, decimal_places=4, null=False)
    calculation = models.ForeignKey(
        OutboundCalculation,
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
    desired_package_type = models.ForeignKey(
        PackageType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="outbound_calculation_items",
    )
    desired_batch = models.ForeignKey(
        "warehouse.Batch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="outbound_calculation_items",
    )
    note = models.TextField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["index", "created"]
        constraints = [
            models.UniqueConstraint(
                fields=["calculation", "index"],
                name="unique_outbound_calculation_item_index",
            )
        ]

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
    state = models.PositiveIntegerField(
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
    state = models.PositiveIntegerField(
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
