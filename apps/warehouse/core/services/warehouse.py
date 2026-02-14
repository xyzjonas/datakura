import uuid
from calendar import monthrange
from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.warehouse.core.exceptions import (
    raise_by_code,
    ErrorCode,
    WarehouseItemBadRequestError,
    WarehouseItemNotFoundError,
    WarehouseOrderNotEditableError,
    WarehouseItemGenericError,
)
from apps.warehouse.core.packaging import get_package_amount_in_product_uom
from apps.warehouse.core.schemas.warehouse import (
    WarehouseOrderCreateSchema,
    InboundWarehouseOrderSchema,
    ProductWarehouseAvailability,
    WarehouseItemSchema,
    InboundWarehouseOrderUpdateSchema,
)
from apps.warehouse.core.services.orders import inbound_orders_service
from apps.warehouse.core.transformation import (
    warehouse_inbound_order_orm_to_schema,
    product_orm_to_schema,
    package_orm_to_schema,
    location_orm_to_schema,
)
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderState,
    InboundOrderItem,
    CreditNoteState,
    CreditNoteToSupplier,
    CreditNoteToSupplierItem,
)
from apps.warehouse.models.packaging import PackageType
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    WarehouseItem,
    WarehouseLocation,
    InboundWarehouseOrderState,
)


def generate_warehouse_item_code() -> str:
    return str(uuid.uuid4())[:13]


def _get_end_of_month(date: datetime) -> datetime:
    last_day = monthrange(date.year, date.month)[1]
    return date.replace(day=last_day)


def _get_month_range(date: datetime) -> tuple[datetime, datetime]:
    last_day = _get_end_of_month(date)
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0), last_day


def raise_if_readonly(order: InboundWarehouseOrder):
    if order.state != InboundWarehouseOrderState.DRAFT:
        raise WarehouseOrderNotEditableError(
            f"order '{order.code}' not in draft anymore ({order.state})"
        )


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
    def get_inbound_warehouse_order(code: str):
        # user = authenticate(
        #     request, username=credentials.username, password=credentials.password
        # )
        order = (
            InboundWarehouseOrder.objects.prefetch_related(
                "items",
                "items__stock_product",
                "items__stock_product__unit_of_measure",
                "items__package_type",
                "items__package_type__unit_of_measure",
            )
            .select_related("order", "order__credit_note")
            .get(code=code)
        )
        return warehouse_inbound_order_orm_to_schema(order)

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
                    code = generate_warehouse_item_code()

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

        if not package.unit_of_measure:
            # no units for a package - special kind that holds any number (carton, pallet)
            package_amount_in_product_uom: float | None = float(warehouse_item.amount)
        else:
            package_amount_in_product_uom = get_package_amount_in_product_uom(
                package, product
            )

        if not package_amount_in_product_uom:
            raise_by_code(
                ErrorCode.INVALID_CONVERSION,
                f"Product's '{product.name}' unit of measure "
                f"'{product.unit_of_measure.name}' can't be "
                f"converted to package '{package.name}' unit of measure "
                f"'{package.unit_of_measure.name if package.unit_of_measure else 'None'}'",
            )

        if amount / package_amount_in_product_uom % 1 != 0:
            raise_by_code(
                ErrorCode.INVALID_CONVERSION,
                f"Product amount '{amount}' ({product.unit_of_measure.name}) doesn't "
                f"fit evenly into the requested package "
                f"'{package.name}' ({package.unit_of_measure.name if package.unit_of_measure else 'None'})",
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

        raise_if_readonly(order)

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
                        code=generate_warehouse_item_code(),
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
    def setup_tracking_for_inbound_order_item(
        order_code: str,
        warehouse_item_code: str,
        to_be_added: list[WarehouseItemSchema],
    ) -> InboundWarehouseOrderSchema:
        """
        Setup tracking for a warehouse item.

        Untracked warehouse item is split into individual warehouse items depending on the
        tracking type (packaging, unique pieces, batches, ...).

        This function makes sure total amounts (UoM) match before and after!
        """
        order = InboundWarehouseOrder.objects.get(code=order_code)
        raise_if_readonly(order)

        untracked_item = WarehouseItem.objects.get(
            code=warehouse_item_code, order_in=order
        )

        remaining_amount = untracked_item.amount - Decimal(
            sum(item.amount for item in to_be_added)
        )
        try:
            with transaction.atomic():
                for new_item in to_be_added:
                    WarehouseItem.objects.create(
                        order_in=order,
                        package_type=PackageType.objects.get(name=new_item.package.type)
                        if new_item.package
                        else None,
                        code=generate_warehouse_item_code(),
                        stock_product=StockProduct.objects.get(
                            code=new_item.product.code
                        ),
                        amount=new_item.amount,
                        location=WarehouseLocation.objects.get(
                            code=new_item.location.code
                        ),
                    )
                if remaining_amount > 0:
                    untracked_item.amount = remaining_amount
                    untracked_item.save()
                else:
                    untracked_item.delete()
        except ObjectDoesNotExist as exc:
            raise WarehouseItemBadRequestError(str(exc))

        return warehouse_inbound_order_orm_to_schema(
            InboundWarehouseOrder.objects.get(code=order_code)
        )

    @staticmethod
    def dissolve_inbound_order_item(
        order_code: str,
        warehouse_item_code: str,
    ) -> InboundWarehouseOrderSchema:
        order = InboundWarehouseOrder.objects.get(code=order_code)

        raise_if_readonly(order)

        item = WarehouseItem.objects.get(code=warehouse_item_code, order_in=order)
        existing_not_packaged = WarehouseItem.objects.filter(
            order_in=order, stock_product=item.stock_product, package_type__isnull=True
        ).first()
        if not item:
            raise WarehouseItemNotFoundError(
                f"No warehouse item with code '{warehouse_item_code}' in order '{order.code}'"
            )
        try:
            with transaction.atomic():
                if not existing_not_packaged:
                    existing_not_packaged = WarehouseItem.objects.create(
                        code=generate_warehouse_item_code(),
                        stock_product=item.stock_product,
                        location=item.location,
                        amount=item.amount,
                        order_in=order,
                    )
                else:
                    existing_not_packaged.amount += item.amount
                    existing_not_packaged.save()

                item.delete()
        except ObjectDoesNotExist as exc:
            raise WarehouseItemBadRequestError(str(exc))

        return warehouse_inbound_order_orm_to_schema(
            InboundWarehouseOrder.objects.get(code=order_code)
        )

    @staticmethod
    def update_inbound_order(
        code: str, body: InboundWarehouseOrderUpdateSchema
    ) -> None:
        order = InboundWarehouseOrder.objects.get(code=code)
        order.state = body.state
        order.save()
        return None

    @classmethod
    def transition_order(cls, code: str, state: InboundWarehouseOrderState) -> None:
        return cls.update_inbound_order(
            code, InboundWarehouseOrderUpdateSchema(state=state)
        )

    @classmethod
    def remove_from_order_to_credit_note(
        cls,
        warehouse_order_code: str,
        warehouse_item_code: str,
        amount: float | Decimal,
    ) -> InboundWarehouseOrderSchema:
        amount = Decimal(amount)
        warehouse_item = (
            WarehouseItem.objects.filter(
                order_in__code=warehouse_order_code, code=warehouse_item_code
            )
            .prefetch_related("stock_product")
            .get()
        )
        stock_product = warehouse_item.stock_product
        warehouse_order = warehouse_item.order_in
        order = warehouse_item.order_in.order

        order_item = InboundOrderItem.objects.filter(
            order=order, stock_product=stock_product
        ).get()
        if warehouse_order.state != InboundWarehouseOrderState.DRAFT:
            raise WarehouseItemGenericError(
                f"Warehouse order '{warehouse_order.code}' is already confirmed and read-only."
            )

        with transaction.atomic():
            if amount > warehouse_item.amount:
                raise WarehouseItemGenericError(
                    f"Requested amount ({amount}) exceeds item amount: {warehouse_item.amount} ({warehouse_item.stock_product.name})"
                )

            note, _ = inbound_orders_service.get_or_create_credit_note(order.code)
            if note.state != CreditNoteState.DRAFT:
                raise WarehouseItemGenericError(
                    f"Credit Note '{note.code}' is already confirmed and read-only"
                )

            code_model = CreditNoteToSupplier.objects.get(code=note.code)
            existing_item = CreditNoteToSupplierItem.objects.filter(
                credit_note__code=note.code, stock_product=stock_product
            ).first()
            if existing_item:
                existing_item.amount += amount
            else:
                existing_item = CreditNoteToSupplierItem.objects.create(
                    stock_product=stock_product,
                    amount=amount,
                    credit_note=code_model,
                    unit_price=order_item.unit_price,
                )

            if amount == warehouse_item.amount:
                warehouse_item.delete()
            else:
                warehouse_item.amount -= amount
                warehouse_item.save()

        return cls.get_inbound_warehouse_order(warehouse_order_code)

    @classmethod
    def confirm_draft(cls, code: str) -> None:
        w_order = cls.get_inbound_warehouse_order(code)
        if w_order.state != InboundWarehouseOrderState.DRAFT:
            raise WarehouseItemGenericError(
                f"Warehouse order '{code}' (state={w_order.state}) has to be in draft state in order to be confirmed."
            )
        cls.transition_order(code, InboundWarehouseOrderState.PENDING)
        inbound_order = InboundOrder.objects.get(warehouse_order__code=code)
        inbound_orders_service.transition_order(
            inbound_order.code, InboundOrderState.PUTAWAY
        )
        if credit_note := getattr(inbound_order, "credit_note", None):
            inbound_orders_service.transition_credit_note(
                credit_note.code, CreditNoteState.CONFIRMED
            )

    @classmethod
    def reset_to_draft(cls, code: str) -> None:
        w_order = cls.get_inbound_warehouse_order(code)
        if w_order.state != InboundWarehouseOrderState.PENDING:
            raise WarehouseItemGenericError(
                f"Warehouse order ${code}, state={w_order.state} has to be in pending state in order to be reset to draft."
            )
        cls.transition_order(code, InboundWarehouseOrderState.DRAFT)
        inbound_order = InboundOrder.objects.get(warehouse_order__code=code)
        inbound_orders_service.transition_order(
            inbound_order.code, InboundOrderState.RECEIVING
        )
        if credit_note := getattr(inbound_order, "credit_note", None):
            inbound_orders_service.transition_credit_note(
                credit_note.code, CreditNoteState.DRAFT
            )

    @classmethod
    def putaway_item(
        cls, item_code, warehouse_order_code: str, new_location_code: str
    ) -> None:
        """
        Putaway an item while processing an inbound order.
        """
        warehouse_order = InboundWarehouseOrder.objects.get(code=warehouse_order_code)
        if warehouse_order.state == InboundWarehouseOrderState.DRAFT:
            raise WarehouseItemGenericError(
                f"Warehouse order '{warehouse_order_code}' is not yet confirmed and thus read-only."
            )

        if warehouse_order.state in (
            InboundWarehouseOrderState.COMPLETED,
            InboundWarehouseOrderState.CANCELLED,
        ):
            raise WarehouseItemGenericError(
                f"Warehouse order ${warehouse_order_code} is already confirmed and/or canceled and thus read-only."
            )

        item = warehouse_order.items.get(code=item_code)
        new_location = WarehouseLocation.objects.get(code=new_location_code)

        existing_same_item = new_location.items.filter(code=item.code).first()
        with transaction.atomic():
            if not existing_same_item:
                item.location = new_location
            else:
                existing_same_item.amount += item.amount
                existing_same_item.save()
                item.delete()
            item.save()

            if warehouse_order.items.filter(location__is_putaway=True).count() == 0:
                cls.transition_order(
                    warehouse_order_code, InboundWarehouseOrderState.COMPLETED
                )
                inbound_orders_service.transition_order(
                    warehouse_order.order.code, InboundOrderState.COMPLETED
                )
            else:
                cls.transition_order(
                    warehouse_order_code, InboundWarehouseOrderState.STARTED
                )

    # @staticmethod
    # def move_item(
    #     item_code: str, location_code: str | None = None, amount: float = None
    # ) -> None:
    #     pass


warehouse_service = WarehouseService()
