from django.db.models import Sum

from apps.warehouse.core.schemas.warehouse import ProductWarehouseAvailability
from apps.warehouse.models.warehouse import WarehouseItem


def get_warehouse_availability(stock_product_code: str) -> float:
    return float(
        WarehouseItem.objects.filter(stock_product__code=stock_product_code)
        .aggregate(total_amount=Sum("amount"))
        .get("total_amount")
        or 0.0
    )


def get_total_availability(stock_product_code: str) -> ProductWarehouseAvailability:
    warehouse_amount = float(
        WarehouseItem.objects.filter(stock_product__code=stock_product_code)
        .aggregate(total_amount=Sum("amount"))
        .get("total_amount")
        or 0.0
    )

    # pending outcoming orders
    out_amount = 0

    return ProductWarehouseAvailability(
        total_amount=warehouse_amount, available_amount=warehouse_amount - out_amount
    )
