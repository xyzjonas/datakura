import uuid
from calendar import monthrange
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.warehouse.core.exceptions import (
    raise_by_code,
    ErrorCode,
    WarehouseItemBadRequestError,
)
from apps.warehouse.core.packaging import get_package_amount_in_product_uom
from apps.warehouse.core.schemas.warehouse import (
    WarehouseOrderCreateSchema,
    InboundWarehouseOrderSchema,
    ProductWarehouseAvailability,
    WarehouseItemSchema,
    InboundWarehouseOrderUpdateSchema,
)
from apps.warehouse.core.transformation import (
    warehouse_inbound_order_orm_to_schema,
    product_orm_to_schema,
    package_orm_to_schema,
    location_orm_to_schema,
)
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderState,
)
from apps.warehouse.models.packaging import PackageType
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    WarehouseItem,
    WarehouseLocation,
)


def _get_end_of_month(date: datetime) -> datetime:
    last_day = monthrange(date.year, date.month)[1]
    return date.replace(day=last_day)


def _get_month_range(date: datetime) -> tuple[datetime, datetime]:
    last_day = _get_end_of_month(date)
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0), last_day


class WarehouseService:
    @staticmethod
    def generate_next_inbound_order_code() -> str:
        now = timezone.now()
        dt_range = _get_month_range(now)
        orders_this_month = InboundWarehouseOrder.objects.filter(
            created__range=dt_range
        ).count()
        return f"P{now.year}{now.month:02d}{orders_this_month + 1:04d}"

    @staticmethod
    def create_inbound_order(
        params: WarehouseOrderCreateSchema,
    ) -> InboundWarehouseOrderSchema:
        purchase_order = InboundOrder.objects.get(code=params.purchase_order_code)
        location = WarehouseLocation.objects.get(code=params.location_code)

        code = WarehouseService.generate_next_inbound_order_code()

        with transaction.atomic():
            warehouse_order = InboundWarehouseOrder.objects.create(
                code=code, order=purchase_order
            )
            for item in purchase_order.items.all():
                if existing_warehouse_item := WarehouseItem.objects.filter(
                    stock_product=item.stock_product
                ).first():
                    code = existing_warehouse_item.code
                    existing_warehouse_item.save()
                else:
                    code = str(uuid.uuid4())

                WarehouseItem.objects.create(
                    code=code,
                    stock_product=item.stock_product,
                    amount=item.amount,
                    location=location,
                    order_in=warehouse_order,
                )
            purchase_order.state = InboundOrderState.RECEIVING
            purchase_order.save()

        return warehouse_inbound_order_orm_to_schema(warehouse_order)

    @staticmethod
    def get_warehouse_availability(stock_product_code: str) -> float:
        return float(
            WarehouseItem.objects.filter(stock_product__code=stock_product_code)
            .aggregate(total_amount=Sum("amount"))
            .get("total_amount")
            or 0.0
        )

    @staticmethod
    def get_total_availability(stock_product_code: str) -> ProductWarehouseAvailability:
        warehouse_amount = float(
            WarehouseItem.objects.filter(
                stock_product__code=stock_product_code, location__is_putaway=False
            )
            .aggregate(total_amount=Sum("amount"))
            .get("total_amount")
            or 0.0
        )

        # todo: pending outcoming orders
        out_amount = 0

        return ProductWarehouseAvailability(
            total_amount=warehouse_amount,
            available_amount=warehouse_amount - out_amount,
        )

    # todo: pass warehouse item code to know about the location codes....
    @staticmethod
    def preview_packaging(
        warehouse_item_id: int, product_code: str, package_name: str, amount: float
    ) -> list[WarehouseItemSchema]:
        warehouse_item = WarehouseItem.objects.get(pk=warehouse_item_id)
        product = StockProduct.objects.get(code=product_code)
        package = PackageType.objects.get(name=package_name)

        package_amount_in_product_uom = get_package_amount_in_product_uom(
            package, product
        )
        if not package_amount_in_product_uom:
            raise_by_code(
                ErrorCode.INVALID_CONVERSION,
                f"Product's '{product.name}' unit of measure "
                f"'{product.unit_of_measure.name}' can't be "
                f"converted to package '{package.name}' unit of measure "
                f"'{package.unit_of_measure.name}'",
            )

        if amount / package_amount_in_product_uom % 1 != 0:
            raise_by_code(
                ErrorCode.INVALID_CONVERSION,
                f"Product amount '{amount}' ({product.unit_of_measure.name}) doesn't "
                f"fit evenly into the requested package "
                f"'{package.name}' ({package.unit_of_measure.name})",
            )

        num_of_packages = round(amount / package_amount_in_product_uom)
        items = []
        for _ in range(num_of_packages):
            items.append(
                WarehouseItemSchema(
                    id=-1,
                    code=warehouse_item.code,
                    product=product_orm_to_schema(product),
                    unit_of_measure=product.unit_of_measure.name,
                    amount=float(package_amount_in_product_uom),
                    package=package_orm_to_schema(package),
                    location=location_orm_to_schema(warehouse_item.location),
                    created=timezone.now(),
                    changed=timezone.now(),
                )
            )

        return items

    @staticmethod
    def add_or_remove_inbound_order_items(
        order_code: str,
        to_be_removed: list[WarehouseItemSchema],
        to_be_added: list[WarehouseItemSchema],
    ) -> InboundWarehouseOrderSchema:
        order = InboundWarehouseOrder.objects.get(code=order_code)
        try:
            with transaction.atomic():
                for item in to_be_removed:
                    order.items.get(pk=item.id).delete()
                for item in to_be_added:
                    WarehouseItem.objects.create(
                        order_in=order,
                        package_type=PackageType.objects.get(name=item.package.type)
                        if item.package
                        else None,
                        code=str(uuid.uuid4()),
                        stock_product=StockProduct.objects.get(code=item.product.code),
                        amount=item.amount,
                        location=WarehouseLocation.objects.get(code=item.location.code),
                    )
        except ObjectDoesNotExist as exc:
            raise WarehouseItemBadRequestError(str(exc))

        return warehouse_inbound_order_orm_to_schema(
            InboundWarehouseOrder.objects.get(code=order_code)
        )

    @staticmethod
    def update_inbound_order(
        code: str, body: InboundWarehouseOrderUpdateSchema
    ) -> InboundWarehouseOrderSchema:
        order = InboundWarehouseOrder.objects.get(code=code)
        order.state = body.state
        order.save()
        return warehouse_inbound_order_orm_to_schema(order)


warehouse_service = WarehouseService()
