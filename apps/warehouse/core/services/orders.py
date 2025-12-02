from calendar import monthrange
from datetime import datetime

from django.db import transaction

from apps.warehouse.core.schemas.orders import (
    IncomingOrderItemCreateSchema,
    IncomingOrderItemSchema,
    IncomingOrderCreateOrUpdateSchema,
    IncomingOrderSchema,
)
from apps.warehouse.core.transformation import (
    incoming_order_item_orm_to_schema,
    incoming_order_orm_to_schema,
)
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.orders import IncomingOrder, IncomingOrderItem
from apps.warehouse.models.product import StockProduct


def _get_end_of_month(date: datetime) -> datetime:
    last_day = monthrange(date.year, date.month)[1]
    return date.replace(day=last_day)


def _get_month_range(date: datetime) -> tuple[datetime, datetime]:
    last_day = _get_end_of_month(date)
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0), last_day


class OrdersService:
    @staticmethod
    def generate_next_incoming_order_code() -> str:
        now = datetime.now()
        dt_range = _get_month_range(now)
        orders_this_month = IncomingOrder.objects.filter(
            created__range=dt_range
        ).count()
        return f"OV{now.year}{now.month:02d}{orders_this_month + 1:04d}"

    @staticmethod
    def update_or_create_incoming(
        params: IncomingOrderCreateOrUpdateSchema, code: str | None = None
    ) -> IncomingOrderSchema:
        if code is None:
            code = OrdersService.generate_next_incoming_order_code()

        supplier = Customer.objects.get(code=params.supplier_code)
        with transaction.atomic():
            order, created = IncomingOrder.objects.update_or_create(
                code=code,
                defaults=dict(
                    external_code=params.external_code,
                    description=params.description,
                    note=params.note,
                    currency=params.currency,
                    supplier=supplier,
                ),
            )

        return incoming_order_orm_to_schema(order)

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
