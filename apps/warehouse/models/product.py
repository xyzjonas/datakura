"""Models related to the stock itself (items, packaging, etc...)"""

from django.db import models

from .base import BaseModel
from .packaging import UnitOfMeasure


class ProductType(BaseModel):
    """Catalogue of all possible product types"""

    name = models.CharField(max_length=255, null=False, unique=True)

    def __str__(self) -> str:
        return self.name


class ProductGroup(BaseModel):
    """Grouping of products"""

    name = models.CharField(max_length=255, null=False, unique=True)
    parent = models.ForeignKey(
        "ProductGroup",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )

    def __str__(self) -> str:
        return self.name


class StockProduct(BaseModel):
    name = models.CharField(max_length=255, null=False)
    code = models.CharField(max_length=255, null=False, unique=True)
    type = models.ForeignKey(ProductType, null=False, on_delete=models.PROTECT)
    group = models.ForeignKey(
        ProductGroup, null=True, blank=True, on_delete=models.SET_NULL
    )
    unit_of_measure = models.ForeignKey(
        UnitOfMeasure,
        null=False,
        on_delete=models.PROTECT,
        related_name="products",
    )
    unit_weight = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name


# class UnitOfMeasureConversionFactor(models.Model):
#     """Conversion factor for a given pair of product -> unit of measure"""
#
#     uom = models.ForeignKey(UnitOfMeasure, null=False, on_delete=models.PROTECT)
#     stock_product = models.ForeignKey(
#         StockProduct, on_delete=models.CASCADE, related_name="conversion_factors"
#     )
#     conversion_factor = models.DecimalField(max_digits=10, decimal_places=4, null=False)
#
#     class Meta:
#         constraints = [
#             UniqueConstraint(fields=["stock_product", "uom"], name="unique_product_uom")
#         ]
#
#     def __str__(self) -> str:
#         return f"{self.stock_product.name} - {self.uom.name} ({self.conversion_factor})"
