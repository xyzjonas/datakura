"""Models related to the warehouse and its sections / partitioning"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet
from django.utils.functional import cached_property

from .base import BaseModel
from .orders import InboundOrder
from .packaging import PackageType
from .product import StockProduct, UnitOfMeasure


# Virtual location?

# Receiving dock? Scan the barcode of the incoming order - unlock the warehouse movement order
# for workers


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

    def __str__(self) -> str:
        return f"{self.warehouse.name} - {self.code}"


class WarehouseItem(BaseModel):
    """Atomic unit of the inventory - uniquely identifiable and trackable item in a warehouse"""

    code = models.CharField(max_length=50, unique=False, null=False)
    stock_product = models.ForeignKey(
        StockProduct,
        null=False,
        on_delete=models.PROTECT,
        help_text="Product information",
    )
    package_type = models.ForeignKey(
        PackageType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="items",
        help_text="Packaging information - in case the item is packaged in some way (optional)",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
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
        "WarehouseOrderIn",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="items",
        help_text="Order which brought the item into the warehouse",
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

        if product_uom.name == package_uom.name:
            return float(self.package_type.amount)

        if product_uom.base_uom and product_uom.base_uom.name == package_uom.name:
            if product_uom.amount_of_base_uom is not None:
                return float(self.package_type.amount / product_uom.amount_of_base_uom)

        if package_uom.base_uom and package_uom.base_uom.name == product_uom.name:
            if package_uom.amount_of_base_uom is not None:
                return float(self.package_type.amount * package_uom.amount_of_base_uom)

        return None

    # 3. Current Quantity
    # remaining = models.DecimalField(max_digits=10, decimal_places=4, null=False)

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
        max_package_amount = ""
        if self.package_type:
            max_package_amount = f"/{self.package_type.amount}"
        uom_name = self.stock_product.unit_of_measure.name

        return (
            f"{self.stock_product.name}, {uom_name} ({self.amount}{max_package_amount})"
        )


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


class WarehouseOrderOut(BaseModel):
    """Warehouse work item - order - move out of the warehouse"""

    code = models.CharField(max_length=50, unique=True, null=False)
    items: QuerySet["WarehouseItem"]

    def __str__(self) -> str:
        return self.code


class WarehouseOrderIn(BaseModel):
    """Warehouse work item - supply - move in the warehouse"""

    code = models.CharField(max_length=50, unique=True, null=False)
    order = models.OneToOneField(
        InboundOrder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="warehouse_order",
    )
    items: QuerySet["WarehouseItem"]

    def __str__(self) -> str:
        return self.code

    @property
    def incoming_order_code(self) -> str | None:
        if hasattr(self, "order") and self.order:
            return self.order.code
        return None
