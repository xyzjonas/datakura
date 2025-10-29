"""Models related to the warehouse and its sections / partitioning"""

from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet, CheckConstraint, Q

from .base import BaseModel
from .product import StockProduct, UnitOfMeasure


class Warehouse(BaseModel):
    """A Warehouse - location / building"""

    name = models.CharField(max_length=50, null=False, unique=True)
    description = models.TextField(null=True, blank=True)
    locations: QuerySet["WarehouseLocation"]

    def __str__(self) -> str:
        return self.name


# Virtual location?

# Receiving dock? Scan the barcode of the incoming order - unlock the warehouse movement order
# for workers


class WarehouseLocation(BaseModel):
    """A single location inside a warehouse"""

    code = models.CharField(max_length=50, null=False, unique=True)
    warehouse = models.ForeignKey(
        Warehouse, null=False, on_delete=models.PROTECT, related_name="locations"
    )
    items: QuerySet["WarehouseItem"]

    def __str__(self) -> str:
        return f"{self.warehouse.name} - {self.code}"


class PackageType(BaseModel):
    """Packaging type - contains n amount of root unit of the stock item"""

    name = models.CharField(max_length=50, null=False, unique=True)
    description = models.TextField(null=True, blank=True)
    count = models.IntegerField(null=False)

    def __str__(self) -> str:
        return self.name


class Load(BaseModel):
    """Represents a physical container (pallet, tote, cart) with a unique identifier."""

    # The unique ID scanned by the warehouse worker (License Plate Number)
    code = models.CharField(max_length=50, unique=True, null=False)

    # The current location of the Load (not the items on it)
    current_location = models.ForeignKey(
        WarehouseLocation,
        null=True,  # Can be null if Load is outside the system
        on_delete=models.SET_NULL,
        related_name="loads",
    )
    # Status (e.g., 'In Use', 'Empty', 'Inspection')
    status = models.CharField(max_length=20, default="In_Use")

    def __str__(self) -> str:
        return self.code


class WarehouseItem(BaseModel):
    """Atomic unit of the inventory - uniquely identifiable and trackable item in a warehouse"""

    code = models.CharField(max_length=50, unique=True, null=False)
    # 1. Product Identity
    stock_item = models.ForeignKey(StockProduct, null=False, on_delete=models.PROTECT)

    # 2. Package Identity (Locking in the received UoM and Factor)
    uom_at_receipt = models.ForeignKey(
        UnitOfMeasure, null=False, on_delete=models.PROTECT
    )
    conversion_factor_at_receipt = models.DecimalField(
        max_digits=10, decimal_places=4, null=False
    )

    # New FK: The Load this item is currently sitting on.
    # When the Load moves, this item moves with it.
    # current_load = models.ForeignKey(
    #     Load,
    #     null=True,  # Null if the item is being handled individually (e.g., small item picking)
    #     blank=True,
    #     on_delete=models.SET_NULL,
    #     related_name="items",
    # )

    warehouse_location = models.ForeignKey(
        WarehouseLocation,
        null=False,
        blank=False,
        on_delete=models.PROTECT,
        related_name="items",
    )

    # 3. Current Quantity
    remaining = models.DecimalField(max_digits=10, decimal_places=4, null=False)

    # class Meta:
    #     constraints = [
    #         CheckConstraint(
    #             check=(
    #                 # Case 1: Load is present, Item is null
    #                 (Q(current_load__isnull=False) & Q(warehouse_location__isnull=True))
    #                 |
    #                 # Case 2: Load is null, Item is present
    #                 (Q(current_load__isnull=True) & Q(warehouse_location__isnull=False))
    #             ),
    #             name="load_or_location_exclusive",
    #         )
    #     ]

    def __str__(self) -> str:
        # Example: Product X, Base UoM: Each. Conversion: Box (Factor 12)
        # Remaining: 5.0000.  Initial Quantity: 12.0000
        initial_count = self.conversion_factor_at_receipt
        uom_name = self.uom_at_receipt.name

        return f"{self.stock_item.name}, {uom_name} ({self.remaining}/{initial_count})"


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

    # 1. FK for Load movements (Bulk movements)
    load = models.ForeignKey(
        Load, null=True, on_delete=models.PROTECT, related_name="movements"
    )

    # 2. FK for individual Item movements
    item = models.ForeignKey(
        WarehouseItem, null=True, on_delete=models.PROTECT, related_name="movements"
    )

    worker = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [
            CheckConstraint(
                check=(
                    # Case 1: Load is present, Item is null
                    (Q(load__isnull=False) & Q(item__isnull=True))
                    |
                    # Case 2: Load is null, Item is present
                    (Q(load__isnull=True) & Q(item__isnull=False))
                ),
                name="load_or_item_exclusive",
            )
        ]


class WarehouseOrderOut(BaseModel):
    """Warehouse work item - order - move out of the warehouse"""

    ...


class WarehouseOrderIn(BaseModel):
    """Warehouse work item - supply - move in the warehouse"""

    ...
