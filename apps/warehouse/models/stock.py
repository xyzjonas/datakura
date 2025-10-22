"""Models related to the stock itself (items, packaging, etc...)"""

from django.db import models

from .base import BaseModel


class StockItem(BaseModel):
    name = models.CharField(max_length=255, null=False)
    code = models.CharField(max_length=255, null=False, unique=True)

    def __str__(self):
        return self.name
