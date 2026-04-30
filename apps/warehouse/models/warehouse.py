"""Models related to the warehouse and its sections / partitioning"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet, Sum
from django.utils import timezone
from django.utils.functional import cached_property

from .barcode import BarcodeMixin
from .base import BaseModel
from .currency import CURRENCY_CHOICES
from .orders import InboundOrder, OutboundOrder
from .packaging import PackageType
from .product import StockProduct, UnitOfMeasure


class Warehouse(BaseModel):
    """A Warehouse - location / building"""

    name = models.CharField(max_length=50, null=False, unique=True)
    description = models.TextField(null=True, blank=True)
    locations: QuerySet["WarehouseLocation"]

    def __str__(self) -> str:
        return self.name


class WarehouseLocation(BaseModel):
    """A single location inside a warehouse"""

    code = models.CharField(max_length=50, null=False, unique=True)
    warehouse = models.ForeignKey(
        Warehouse, null=False, on_delete=models.PROTECT, related_name="locations"
    )
    items: QuerySet["WarehouseItem"]
    is_putaway = models.BooleanField(default=False)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.warehouse.name} - {self.code}"


class TrackingLevel(models.TextChoices):
    SERIALIZED_PIECE = "SERIALIZED_PIECE", "Individual Pieces"
    SERIALIZED_PACKAGE = "SERIALIZED_PACKAGE", "Individual Packages"
    BATCH = "BATCH", "Batch Tracked"
    FUNGIBLE = "FUNGIBLE", "Fully Fungible"


class Batch(BaseModel, BarcodeMixin):
    description = models.CharField(max_length=300, null=True, blank=True)


class AvailableWarehouseItemQuerySet(models.QuerySet["WarehouseItem"]):
    def total_amount(self, product_code: str | None = None) -> Decimal:
        queryset = self
        if product_code is not None:
            queryset = queryset.filter(stock_product__code=product_code)

        return queryset.aggregate(total_amount=Sum("amount")).get(
            "total_amount"
        ) or Decimal("0")


class AvailableWarehouseItemManager(
    models.Manager.from_queryset(AvailableWarehouseItemQuerySet)  # type: ignore
):
    def get_queryset(self) -> AvailableWarehouseItemQuerySet:
        return cast(
            AvailableWarehouseItemQuerySet,
            super()
            .get_queryset()
            .exclude(
                order_in__state__in=(
                    InboundWarehouseOrderState.DRAFT,
                    InboundWarehouseOrderState.IN_TRANSIT,
                )
            )
            .exclude(location__is_putaway=True)
            .exclude(outbound_assignment__isnull=False),
        )

    def filter(self, *args: Any, **kwargs: Any) -> AvailableWarehouseItemQuerySet:
        return cast(AvailableWarehouseItemQuerySet, super().filter(*args, **kwargs))

    def total_amount(self, product_code: str | None = None) -> Decimal:
        return self.get_queryset().total_amount(product_code=product_code)


class PhysicalWarehouseItemManager(
    models.Manager.from_queryset(AvailableWarehouseItemQuerySet)  # type: ignore
):
    def get_queryset(self) -> AvailableWarehouseItemQuerySet:
        return cast(
            AvailableWarehouseItemQuerySet,
            super().get_queryset().exclude(outbound_assignment__isnull=False),
        )

    def filter(self, *args: Any, **kwargs: Any) -> AvailableWarehouseItemQuerySet:
        return cast(AvailableWarehouseItemQuerySet, super().filter(*args, **kwargs))

    def total_amount(self, product_code: str | None = None) -> Decimal:
        return self.get_queryset().total_amount(product_code=product_code)


class WarehouseItem(BaseModel, BarcodeMixin):
    """Atomic unit of the inventory - uniquely identifiable and trackable item in a warehouse"""

    objects = models.Manager()
    available = AvailableWarehouseItemManager()
    physical_stock = PhysicalWarehouseItemManager()

    stock_product = models.ForeignKey(
        StockProduct,
        null=False,
        on_delete=models.PROTECT,
        help_text="Product information",
    )
    tracking_level = models.CharField(
        max_length=20,
        choices=TrackingLevel.choices,
        default=TrackingLevel.FUNGIBLE,
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Amount of the stock product in stock product UOM",
    )
    location = models.ForeignKey(
        WarehouseLocation,
        null=False,
        blank=False,
        on_delete=models.PROTECT,
        related_name="items",
        help_text="Location where the physical item is stored in the warehouse",
    )
    order_in = models.ForeignKey(
        "InboundWarehouseOrder",
        on_delete=models.SET_NULL,
        related_name="items",
        help_text="Order item which brought the item into the warehouse",
        null=True,
        blank=True,
    )
    source_order_item = models.ForeignKey(
        "InboundWarehouseOrderItem",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="warehouse_items",
        help_text="Frozen snapshot line that produced this item (set at confirmation, never changed)",
    )
    # Optional fields - populated based on tracking_level
    batch = models.ForeignKey(
        "Batch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="inventory",
        help_text="Required for BATCH and SERIALIZED_* levels",
    )
    package_type = models.ForeignKey(
        PackageType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="items",
        help_text="Packaging information - in case the item is packaged in some way (optional)",
    )

    @cached_property
    def unit_of_measure(self) -> UnitOfMeasure:
        return self.stock_product.unit_of_measure

    @cached_property
    def package_amount_in_product_uom(self) -> float | None:
        if not self.package_type:
            return None

        product_uom = self.stock_product.unit_of_measure
        package_uom = self.package_type.unit_of_measure
        if not package_uom:
            return None

        if product_uom.name == package_uom.name:
            return float(self.package_type.amount)

        if product_uom.base_uom and product_uom.base_uom.name == package_uom.name:
            if product_uom.amount_of_base_uom is not None:
                return float(self.package_type.amount / product_uom.amount_of_base_uom)

        if package_uom.base_uom and package_uom.base_uom.name == product_uom.name:
            if package_uom.amount_of_base_uom is not None:
                return float(self.package_type.amount * package_uom.amount_of_base_uom)

        return None


class WarehouseMovement(models.Model):
    """Traceability: Tracks the movement of a Load OR a single Item."""

    moved_at = models.DateTimeField(auto_now=True)
    # Movement endpoints remain the same
    location_from = models.ForeignKey(
        WarehouseLocation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="movements_from",
    )
    location_to = models.ForeignKey(
        WarehouseLocation,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="movements_to",
    )
    inbound_order_code = models.ForeignKey(
        "InboundWarehouseOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warehouse_movements",
    )
    outbound_order_code = models.ForeignKey(
        "OutboundWarehouseOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="warehouse_movements",
    )

    stock_product = models.ForeignKey(
        StockProduct, on_delete=models.PROTECT, related_name="warehouse_movements"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Amount of the stock product in stock product UOM",
    )
    item = models.ForeignKey(
        WarehouseItem,
        null=True,
        on_delete=models.SET_NULL,
        related_name="movements",
        help_text="Track item ID for non-fungible items",
    )
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)
    worker = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)


###################################################################################
# ORDERS
###################################################################################


class InboundWarehouseOrderState(models.IntegerChoices):
    IN_TRANSIT = 1, "In Transit"
    DRAFT = 2, "Draft"
    PENDING = 3, "Pending"
    STARTED = 4, "Started"
    COMPLETED = 5, "Completed"
    CANCELLED = 6, "Cancelled"

    @classmethod
    def get_label(cls, value):
        """Return the API string for a given state value."""
        member = value if isinstance(value, cls) else cls(value)
        api_values = {
            cls.IN_TRANSIT: "in transit",
            cls.DRAFT: "draft",
            cls.PENDING: "pending",
            cls.STARTED: "started",
            cls.COMPLETED: "completed",
            cls.CANCELLED: "cancelled",
        }
        if member in api_values:
            return api_values[member]
        return str(value)


class OutboundWarehouseOrderState(models.IntegerChoices):
    DRAFT = 1, "Draft"
    PENDING = 2, "Pending"
    STARTED = 3, "Started"
    COMPLETED = 4, "Completed"
    CANCELLED = 5, "Cancelled"

    @classmethod
    def get_label(cls, value):
        """Return the API string for a given state value."""
        member = value if isinstance(value, cls) else cls(value)
        api_values = {
            cls.DRAFT: "draft",
            cls.PENDING: "pending",
            cls.STARTED: "started",
            cls.COMPLETED: "completed",
            cls.CANCELLED: "cancelled",
        }
        if member in api_values:
            return api_values[member]
        return str(value)


class OutboundWarehouseOrder(BaseModel):
    """Warehouse work item - order - move out of the warehouse"""

    code = models.CharField(max_length=50, unique=True, null=False)
    order = models.ForeignKey(
        OutboundOrder,
        on_delete=models.PROTECT,
        related_name="warehouse_orders",
        null=True,
        blank=True,
    )
    items: QuerySet["WarehouseItem"]
    order_items: QuerySet["OutboundWarehouseOrderItem"]
    derived_orders: QuerySet["OutboundWarehouseOrder"]
    warehouse_movements: QuerySet["WarehouseMovement"]
    state = models.PositiveIntegerField(
        choices=OutboundWarehouseOrderState,
        default=OutboundWarehouseOrderState.DRAFT,
    )
    primary_order = models.ForeignKey(
        "OutboundWarehouseOrder",
        on_delete=models.CASCADE,
        related_name="derived_orders",
        help_text="Primary order that this order is derived from",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return self.code


class OutboundWarehouseOrderItem(BaseModel):
    """Frozen outbound picking requirement linked to exactly one warehouse item when picked."""

    warehouse_order = models.ForeignKey(
        OutboundWarehouseOrder,
        on_delete=models.CASCADE,
        related_name="order_items",
    )
    source_order_item = models.ForeignKey(
        "warehouse.OutboundOrderItem",
        on_delete=models.CASCADE,
        related_name="warehouse_order_items",
    )
    stock_product = models.ForeignKey(
        StockProduct,
        null=False,
        on_delete=models.PROTECT,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=4)
    desired_package_type = models.ForeignKey(
        PackageType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="outbound_warehouse_order_items",
    )
    desired_batch = models.ForeignKey(
        Batch,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="outbound_warehouse_order_items",
    )
    warehouse_item = models.OneToOneField(
        WarehouseItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="outbound_assignment",
    )
    index = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["index", "created"]

    def __str__(self) -> str:
        return (
            f"{self.amount} × {self.stock_product.name} ({self.warehouse_order.code})"
        )


class InboundWarehouseOrder(BaseModel):
    """Warehouse work item - supply - move in the warehouse"""

    code = models.CharField(max_length=50, unique=True, null=False)
    order = models.ForeignKey(
        InboundOrder,
        on_delete=models.PROTECT,
        related_name="warehouse_orders",
    )
    items: QuerySet[WarehouseItem]
    order_items: QuerySet["InboundWarehouseOrderItem"]
    derived_orders: QuerySet["InboundWarehouseOrder"]
    warehouse_movements: QuerySet["WarehouseMovement"]
    state = models.PositiveIntegerField(
        choices=InboundWarehouseOrderState,
        default=InboundWarehouseOrderState.DRAFT,
    )
    primary_order = models.ForeignKey(
        "InboundWarehouseOrder",
        on_delete=models.CASCADE,
        related_name="derived_orders",
        help_text="Primary order that this order is derived from",
        null=True,
        blank=True,
    )
    pickup_location = models.ForeignKey(
        WarehouseLocation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inbound_pickup_orders",
        help_text="Location where goods are staged upon arrival confirmation",
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return self.code


class InboundWarehouseOrderItem(BaseModel):
    """
    Immutable snapshot of a single line item on an inbound warehouse order.

    Created when arrival is confirmed (IN_TRANSIT → DRAFT).  Editable
    (tracking level, packaging, amounts) only while the warehouse order is
    in DRAFT state.  Locked at confirmation (DRAFT → PENDING), at which
    point live WarehouseItem records are materialised from these rows.
    """

    warehouse_order = models.ForeignKey(
        InboundWarehouseOrder,
        on_delete=models.CASCADE,
        related_name="order_items",
    )
    stock_product = models.ForeignKey(
        StockProduct,
        null=False,
        on_delete=models.PROTECT,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=4)
    tracking_level = models.CharField(
        max_length=20,
        choices=TrackingLevel.choices,
        default=TrackingLevel.FUNGIBLE,
    )
    package_type = models.ForeignKey(
        PackageType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    unit_price_at_receipt = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text="Unit price frozen from the purchase order at arrival confirmation",
    )
    index = models.PositiveIntegerField(default=0)
    # Stores the batch barcode string during DRAFT so the actual Batch object
    # can be created when WarehouseItems are materialised on confirmation.
    batch_barcode = models.CharField(max_length=200, null=True, blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["index", "created"]

    def __str__(self) -> str:
        return (
            f"{self.amount} × {self.stock_product.name} ({self.warehouse_order.code})"
        )


class InventorySnapshotTriggerSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    SCHEDULED = "scheduled", "Scheduled"


class InventorySnapshot(BaseModel):
    captured_at = models.DateTimeField(default=timezone.now, db_index=True)
    trigger_source = models.CharField(
        max_length=32,
        choices=InventorySnapshotTriggerSource.choices,
        default=InventorySnapshotTriggerSource.MANUAL,
    )
    cadence = models.CharField(max_length=32, null=True, blank=True)
    bucket_key = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    line_count = models.PositiveIntegerField(default=0)
    purchase_totals_by_currency = models.JSONField(default=dict, blank=True)
    receipt_totals_by_currency = models.JSONField(default=dict, blank=True)
    receipt_unpriced_line_count = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["-captured_at", "-created"]
        constraints = [
            models.UniqueConstraint(
                fields=["trigger_source", "cadence", "bucket_key"],
                condition=models.Q(
                    trigger_source=InventorySnapshotTriggerSource.SCHEDULED,
                    cadence__isnull=False,
                    bucket_key__isnull=False,
                ),
                name="warehouse_inventorysnapshot_scheduled_bucket_unique",
            )
        ]

    def __str__(self) -> str:
        return f"Snapshot #{self.pk} @ {self.captured_at.isoformat()}"


class InventorySnapshotLine(BaseModel):
    snapshot = models.ForeignKey(
        InventorySnapshot,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    warehouse_item = models.ForeignKey(
        WarehouseItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_snapshot_lines",
    )
    warehouse_item_id_at_snapshot = models.PositiveBigIntegerField()
    stock_product = models.ForeignKey(
        StockProduct,
        on_delete=models.PROTECT,
        related_name="inventory_snapshot_lines",
    )
    product_code = models.CharField(max_length=255)
    product_name = models.CharField(max_length=255)
    location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.PROTECT,
        related_name="inventory_snapshot_lines",
    )
    location_code = models.CharField(max_length=50)
    source_order_item = models.ForeignKey(
        InboundWarehouseOrderItem,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_snapshot_lines",
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=4)
    unit_of_measure = models.CharField(max_length=64)
    tracking_level = models.CharField(max_length=20, choices=TrackingLevel.choices)
    purchase_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="CZK",
    )
    purchase_unit_price = models.DecimalField(max_digits=10, decimal_places=4)
    purchase_line_value = models.DecimalField(max_digits=14, decimal_places=4)
    receipt_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        null=True,
        blank=True,
    )
    receipt_unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
    )
    receipt_line_value = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )
    receipt_price_available = models.BooleanField(default=False)
    receipt_price_fallback_reason = models.CharField(
        max_length=64,
        null=True,
        blank=True,
    )

    class Meta(BaseModel.Meta):
        ordering = ["product_code", "location_code", "warehouse_item_id_at_snapshot"]

    def __str__(self) -> str:
        return f"Snapshot line #{self.pk} - {self.product_code} @ {self.location_code}"
