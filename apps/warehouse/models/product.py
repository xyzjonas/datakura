"""Models related to the stock itself (items, packaging, etc...)"""

from django.db import models
from django.db.models import Q

from .base import BaseModel
from .barcode import BarcodeMixin
from .currency import CURRENCY_CHOICES
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


class StockProduct(BaseModel, BarcodeMixin):
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

    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CZK")
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    customs_declaration_group = models.CharField(max_length=255, null=True, blank=True)

    attributes = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta, BarcodeMixin.Meta):
        ordering = ["code"]

    def __str__(self):
        return self.name


class PriceGroup(BaseModel):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(
                condition=Q(discount_percent__gte=0) & Q(discount_percent__lte=100),
                name="warehouse_pricegroup_discount_range",
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name} ({self.discount_percent}%)"


class StockProductPrice(BaseModel):
    product = models.ForeignKey(
        StockProduct,
        null=False,
        on_delete=models.CASCADE,
        related_name="dynamic_prices",
    )
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    customer = models.ForeignKey(
        "warehouse.Customer",
        null=False,
        on_delete=models.CASCADE,
        related_name="product_prices",
    )

    class Meta(BaseModel.Meta):
        ordering = ["product", "customer", "discount_percent"]
        constraints = [
            models.CheckConstraint(
                condition=Q(discount_percent__gte=0) & Q(discount_percent__lte=100),
                name="warehouse_productprice_discount_range",
            ),
            models.CheckConstraint(
                condition=Q(customer__isnull=False),
                name="warehouse_productprice_customer_required",
            ),
            models.UniqueConstraint(
                fields=["product", "customer"],
                name="warehouse_unique_product_customer_discount",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.code} - {self.customer.code} ({self.discount_percent}%)"
