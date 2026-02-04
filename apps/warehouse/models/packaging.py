from .base import BaseModel
from django.db import models


class UnitOfMeasure(BaseModel):
    """Catalogue of all the possible "units of measure" - UoC"""

    name = models.CharField(max_length=255, null=False, unique=True)
    amount_of_base_uom = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    base_uom = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="sub_units",
    )

    def __str__(self) -> str:
        return self.name


class PackageType(BaseModel):
    """
    Packaging type - contains n amount of root unit of the stock item

    IF a package type has NO unit of measure: it can take on any amount of a particular
    stock product! Thus becoming a mere 'vessel' for a certain amount of a product -
    e.g. a pallet - for easier bulk transfers or temporary stow-away.
    """

    name = models.CharField(max_length=50, null=False, unique=True)
    description = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=4, null=False)
    unit_of_measure = models.ForeignKey(
        UnitOfMeasure,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="package_types",
    )

    def __str__(self) -> str:
        return self.name
