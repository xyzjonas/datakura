from django.db import models
from django.db.models import QuerySet

from .base import BaseModel
from .currency import CURRENCY_CHOICES
from .customer import Customer
from .product import StockProduct


class IncomingOrder(BaseModel):
    """Incoming order"""

    code = models.CharField(max_length=50, null=False, unique=True)
    external_code = models.CharField(
        max_length=50, null=True, blank=True
    )  # todo: add unique constraint
    description = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    supplier = models.ForeignKey(Customer, null=False, on_delete=models.PROTECT)
    items: QuerySet["IncomingOrderItem"]

    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CZK")

    def __str__(self) -> str:
        return f"{self.code} | {self.supplier.name}"


class IncomingOrderItem(BaseModel):
    """Incoming order"""

    stock_product = models.ForeignKey(
        StockProduct, null=False, on_delete=models.PROTECT
    )
    amount = models.DecimalField(max_digits=10, decimal_places=4, null=False)
    order = models.ForeignKey(
        IncomingOrder,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="items",
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    def __str__(self):
        return f"{self.amount} × {self.stock_product.name}"
