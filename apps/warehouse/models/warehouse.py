"""Models related to the warehouse and its sections / partitioning"""

from django.db import models
from django.db.models import QuerySet

from .base import BaseModel
from .stock import StockItem


class Warehouse(BaseModel):
    """A Warehouse - location / building"""

    name = models.CharField(max_length=20, null=False, unique=True)
    description = models.TextField(null=True, blank=True)
    locations: QuerySet["WarehouseLocation"]

    def __str__(self) -> str:
        return self.name


class WarehouseLocation(BaseModel):
    """A single location inside a warehouse"""

    code = models.CharField(max_length=20, null=False, unique=True)
    warehouse = models.ForeignKey(
        Warehouse, null=False, on_delete=models.PROTECT, related_name="locations"
    )
    items: QuerySet["WarehouseItem"]

    def __str__(self) -> str:
        return f"{self.warehouse.name} - {self.code}"


class PackageType(BaseModel):
    """Packaging type - contains n amount of root unit of the stock item"""

    name = models.CharField(max_length=255, null=False, unique=True)
    description = models.TextField(null=True, blank=True)
    count = models.IntegerField(null=False)

    def __str__(self) -> str:
        return self.name


class WarehouseItem(BaseModel):
    """Atomic unit of the inventory - uniquely identifiable and trackable item in a warehouse"""

    stock_item = models.ForeignKey(StockItem, null=False, on_delete=models.PROTECT)
    package_type = models.ForeignKey(PackageType, null=False, on_delete=models.PROTECT)
    remaining = models.IntegerField(null=False)

    warehouse_location = models.ForeignKey(
        WarehouseLocation, null=False, on_delete=models.PROTECT, related_name="items"
    )

    def __str__(self) -> str:
        count = f"{self.remaining}/{self.package_type.count}"
        return f"{self.stock_item.name}, {self.package_type.name} ({count})"


class WarehouseMovement(BaseModel):
    """Traceability: any movement of any warehouse item from A to B or in/out of the warehouse"""

    location_from = models.ForeignKey(
        WarehouseLocation,
        null=True,
        on_delete=models.CASCADE,
        related_name="movements_from",
    )
    location_to = models.ForeignKey(
        WarehouseLocation,
        null=True,
        on_delete=models.CASCADE,
        related_name="movements_to",
    )


class WarehouseOrderOut(BaseModel):
    """Warehouse work item - order - move out of the warehouse"""

    ...


class WarehouseOrderIn(BaseModel):
    """Warehouse work item - supply - move in the warehouse"""

    ...
