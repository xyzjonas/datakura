from django.db import models

from .base import BaseModel
from .customer import Customer
from .product import StockProduct


class IncomingOrderItem(BaseModel):
    """Incoming order"""

    stock_product = models.ForeignKey(
        StockProduct, null=False, on_delete=models.PROTECT
    )
    amount = models.DecimalField(max_digits=10, decimal_places=4, null=False)


class IncomingOrder(BaseModel):
    """Incoming order"""

    code = models.CharField(max_length=50, null=False, unique=True)
    external_code = models.CharField(
        max_length=50, null=True, blank=True
    )  # todo: add unique constraint
    description = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    supplier = models.ForeignKey(Customer, null=False, on_delete=models.PROTECT)

    def __str__(self) -> str:
        return f"{self.code} | {self.supplier.name}"
