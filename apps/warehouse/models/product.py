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


class DynamicPriceType(models.TextChoices):
    GROUP_DISCOUNT = "GROUP_DISCOUNT", "Generic group discount"
    CUSTOMER_DISCOUNT = "CUSTOMER_DISCOUNT", "Customer discount"


class PriceGroup(BaseModel):
    name = models.CharField(max_length=255, unique=True)

    class Meta(BaseModel.Meta):
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class StockProductPrice(BaseModel):
    product = models.ForeignKey(
        StockProduct,
        null=False,
        on_delete=models.CASCADE,
        related_name="dynamic_prices",
    )
    price_type = models.CharField(
        max_length=32,
        choices=DynamicPriceType.choices,
    )
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    group = models.ForeignKey(
        PriceGroup,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    customer = models.ForeignKey(
        "warehouse.Customer",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="product_prices",
    )

    class Meta(BaseModel.Meta):
        ordering = ["product", "price_type", "discount_percent"]
        constraints = [
            models.CheckConstraint(
                condition=Q(discount_percent__gte=0) & Q(discount_percent__lte=100),
                name="warehouse_productprice_discount_range",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        price_type=DynamicPriceType.GROUP_DISCOUNT,
                        group__isnull=False,
                        customer__isnull=True,
                    )
                    | Q(
                        price_type=DynamicPriceType.CUSTOMER_DISCOUNT,
                        customer__isnull=False,
                        group__isnull=True,
                    )
                ),
                name="warehouse_productprice_target_by_type",
            ),
            models.UniqueConstraint(
                fields=["product", "group"],
                condition=Q(
                    price_type=DynamicPriceType.GROUP_DISCOUNT,
                    group__isnull=False,
                ),
                name="warehouse_unique_product_group_discount",
            ),
            models.UniqueConstraint(
                fields=["product", "customer"],
                condition=Q(
                    price_type=DynamicPriceType.CUSTOMER_DISCOUNT,
                    customer__isnull=False,
                ),
                name="warehouse_unique_product_customer_discount",
            ),
        ]

    def __str__(self) -> str:
        if self.group:
            target = self.group.name
        elif self.customer:
            target = self.customer.code
        else:
            target = "-"
        return (
            f"{self.product.code} - {self.price_type} - {target} "
            f"({self.discount_percent}%)"
        )
