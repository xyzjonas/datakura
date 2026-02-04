from calendar import monthrange
from datetime import datetime

from django.db import transaction
from django.template.loader import get_template
from django.utils import timezone
from loguru import logger
from weasyprint import HTML  # type: ignore

from apps.warehouse.core.schemas.orders import (
    InboundOrderItemCreateSchema,
    InboundOrderItemSchema,
    InboundOrderCreateOrUpdateSchema,
    InboundOrderSchema,
)
from apps.warehouse.core.services.products import stock_product_service
from apps.warehouse.core.transformation import (
    inbound_order_item_orm_to_schema,
    inbound_order_orm_to_schema,
)
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderItem,
    InboundOrderState,
)
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
        now = timezone.now()
        dt_range = _get_month_range(now)
        orders_this_month = InboundOrder.objects.filter(created__range=dt_range).count()
        return f"OV{now.year}{now.month:02d}{orders_this_month + 1:04d}"

    @staticmethod
    def update_or_create_incoming(
        params: InboundOrderCreateOrUpdateSchema, code: str | None = None
    ) -> InboundOrderSchema:
        if code is None:
            # todo: create code only after transitioning from 'draft'
            code = OrdersService.generate_next_incoming_order_code()

        supplier = Customer.objects.get(code=params.supplier_code)
        with transaction.atomic():
            order, created = InboundOrder.objects.update_or_create(
                code=code,
                defaults=dict(
                    external_code=params.external_code,
                    description=params.description,
                    note=params.note,
                    currency=params.currency,
                    supplier=supplier,
                ),
            )

        return inbound_order_orm_to_schema(order)

    @staticmethod
    def add_item(
        code: str, item: InboundOrderItemCreateSchema
    ) -> InboundOrderItemSchema:
        order = InboundOrder.objects.get(code=code)
        stock_product = StockProduct.objects.get(code=item.product_code)
        with transaction.atomic():
            item_model = InboundOrderItem.objects.create(
                stock_product=stock_product,
                amount=item.amount,
                order=order,
                unit_price=item.unit_price,
            )

        return inbound_order_item_orm_to_schema(item_model)

    @staticmethod
    def remove_item(code: str, product_code: str) -> bool:
        order = InboundOrder.objects.get(code=code)
        items = InboundOrderItem.objects.filter(
            order=order, stock_product__code=product_code
        )
        with transaction.atomic():
            items.delete()

        return True

    @staticmethod
    def transition_order(code: str, new_state: InboundOrderState) -> InboundOrderSchema:
        # todo: audit log
        order = InboundOrder.objects.get(code=code)
        with transaction.atomic():
            old_state = order.state
            order.state = new_state

            order.save()
            logger.info(
                f"Inboud order '{order.code}' transitioned: {old_state} -> {new_state}"
            )

        return inbound_order_orm_to_schema(order)

    @classmethod
    def accept_inbound_order(cls, order_code: str):
        order = InboundOrder.objects.get(code=order_code)
        cls.transition_order(order_code, InboundOrderState.RECEIVING)
        for item in order.items.all():
            stock_product_service.update_pricing(item.stock_product.code)

    @staticmethod
    def get_html(code: str) -> str:
        order = InboundOrder.objects.get(code=code)
        order_schema = inbound_order_orm_to_schema(order)
        template = get_template("inbound_order.html")
        html_content = template.render({"order": order_schema.model_dump()})

        return html_content

    @classmethod
    def get_pdf(cls, code: str) -> bytes:
        return HTML(string=cls.get_html(code)).write_pdf()


inbound_orders_service = OrdersService()
