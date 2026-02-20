"""Models related to the warehouse and its sections / partitioning"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet
from django.utils.functional import cached_property

from .barcode import BarcodeMixin
from .base import BaseModel
from .orders import InboundOrder
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


class WarehouseItem(BaseModel, BarcodeMixin):
    """Atomic unit of the inventory - uniquely identifiable and trackable item in a warehouse"""

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


class WarehouseMovement(BaseModel):
    """Traceability: Tracks the movement of a Load OR a single Item."""

    # Movement endpoints remain the same
    location_from = models.ForeignKey(
        WarehouseLocation,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="movements_from",
    )
    location_to = models.ForeignKey(
        WarehouseLocation,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="movements_to",
    )

    # todo: bulk move? Boxes? Pallets?

    item = models.ForeignKey(
        WarehouseItem, null=True, on_delete=models.PROTECT, related_name="movements"
    )

    worker = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)


###################################################################################
# ORDERS
###################################################################################


class InboundWarehouseOrderState(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending"
    STARTED = "started", "Started"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class OutboundWarehouseOrder(BaseModel):
    """Warehouse work item - order - move out of the warehouse"""

    code = models.CharField(max_length=50, unique=True, null=False)
    items: QuerySet["WarehouseItem"]

    def __str__(self) -> str:
        return self.code


class InboundWarehouseOrder(BaseModel):
    """Warehouse work item - supply - move in the warehouse"""

    code = models.CharField(max_length=50, unique=True, null=False)
    order = models.OneToOneField(
        InboundOrder,
        on_delete=models.PROTECT,
        related_name="warehouse_order",
    )
    items: QuerySet[WarehouseItem]
    state = models.CharField(
        choices=InboundWarehouseOrderState,
        default=InboundWarehouseOrderState.DRAFT,
        max_length=30,
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return self.code
