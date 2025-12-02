from django.db import transaction

from apps.warehouse.core.schemas.orders import (
    IncomingOrderItemCreateSchema,
    IncomingOrderItemSchema,
)
from apps.warehouse.core.transformation import incoming_order_item_orm_to_schema
from apps.warehouse.models.orders import IncomingOrder, IncomingOrderItem
from apps.warehouse.models.product import StockProduct


class OrdersService:
    @staticmethod
    def add_item(
        code: str, item: IncomingOrderItemCreateSchema
    ) -> IncomingOrderItemSchema:
        order = IncomingOrder.objects.get(code=code)
        stock_product = StockProduct.objects.get(code=item.product_code)
        with transaction.atomic():
            item_model = IncomingOrderItem.objects.create(
                stock_product=stock_product,
                amount=item.amount,
                order=order,
                unit_price=item.unit_price,
            )

        return incoming_order_item_orm_to_schema(item_model)

    @staticmethod
    def remove_item(code: str, product_code: str) -> bool:
        order = IncomingOrder.objects.get(code=code)
        items = IncomingOrderItem.objects.filter(
            order=order, stock_product__code=product_code
        )
        with transaction.atomic():
            items.delete()

        return True


incoming_orders_service = OrdersService()
