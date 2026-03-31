import uuid
from calendar import monthrange
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone

from apps.warehouse.core.exceptions import (
    raise_by_code,
    ErrorCode,
    WarehouseItemBadRequestError,
    WarehouseItemNotFoundError,
    WarehouseOrderNotEditableError,
    WarehouseGenericError,
)
from apps.warehouse.core.packaging import get_package_amount_in_product_uom
from apps.warehouse.core.schemas.barcode import BarcodeSchema
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.schemas.warehouse import (
    AuditTimelineEntrySchema,
    WarehouseOrderCreateSchema,
    InboundWarehouseOrderSchema,
    ProductWarehouseAvailability,
    WarehouseItemDetailSchema,
    WarehouseItemSchema,
    InboundWarehouseOrderUpdateSchema,
    BatchSchema,
)
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.orders import inbound_orders_service
from apps.warehouse.core.transformation import (
    warehouse_inbound_order_orm_to_schema,
    product_orm_to_schema,
    package_orm_to_schema,
    location_orm_to_schema,
    warehouse_item_orm_to_schema,
)
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.barcode import BarcodeType, Barcode
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
    WarehouseMovement,
    WarehouseLocation,
    InboundWarehouseOrderState,
    TrackingLevel,
    Batch,
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


def get_or_create_batch(batch_barcode: str) -> tuple[Batch, bool]:
    barcode = (
        Barcode.objects.select_related("content_type")
        .filter(code=batch_barcode)
        .first()
    )
    if barcode and barcode.content_type.model_class() is not Batch:
        raise_by_code(
            ErrorCode.INVALID_BARCODE,
            f"Existing barcode type is invalid, {type(barcode.content_object)}, expected Batch",
        )
    if barcode:
        return barcode.content_object, False  # type: ignore

    batch = Batch.objects.create()
    batch.attach_barcode(batch_barcode, is_primary=True)
    return batch, True


class MovementService:
    @staticmethod
    def move_item(
        item: WarehouseItem,
        context: RequestContext,
        new_location_or_code: WarehouseLocation | str,
        amount: Decimal | None = None,
    ) -> None:
        location_from = item.location
        amount = amount or item.amount
        if isinstance(new_location_or_code, str):
            new_location = WarehouseLocation.objects.get(code=new_location_or_code)
        else:
            new_location = new_location_or_code

        movement_item = None
        movement_batch = None

        if item.tracking_level in (
            TrackingLevel.SERIALIZED_PACKAGE,
            TrackingLevel.SERIALIZED_PIECE,
        ):
            item.location = new_location
            item.save()
            movement_item = item

        elif item.tracking_level == TrackingLevel.BATCH:
            movement_batch = item.batch
            existing_of_the_same_batch = new_location.items.filter(
                batch=item.batch
            ).first()
            if existing_of_the_same_batch:
                existing_of_the_same_batch.amount += amount
                existing_of_the_same_batch.save()
                if amount == item.amount:
                    item.delete()
                    movement_item = existing_of_the_same_batch
                else:
                    old_amount = item.amount
                    item.amount -= amount
                    item.save()
                    movement_item = item
                    audit_service.add_entry(
                        item,
                        action=AuditAction.UPDATE,
                        user=context.user_id,
                        reason=AuditMessages.ITEM_PARTIALLY_MOVED.CS,
                        changes={
                            "amount": {"old": str(old_amount), "new": str(item.amount)}
                        },
                    )
            else:
                movement_item = item
                if amount == item.amount:
                    item.location = new_location
                    item.save()
                else:
                    old_amount = item.amount
                    item.amount -= amount
                    item.save()
                    new_item = WarehouseItem.objects.create(
                        stock_product=item.stock_product,
                        tracking_level=item.tracking_level,
                        amount=amount,
                        location=new_location,
                        order_in=item.order_in,
                        batch=item.batch,
                    )
                    audit_service.add_entry(
                        new_item,
                        action=AuditAction.CREATE,
                        user=context.user_id,
                        reason=AuditMessages.ITEM_CREATED_BY_PARTIAL_MOVE.CS,
                        changes={
                            "amount": {"old": str(old_amount), "new": str(item.amount)}
                        },
                    )
                    audit_service.add_entry(
                        item,
                        action=AuditAction.UPDATE,
                        user=context.user_id,
                        reason=AuditMessages.ITEM_PARTIALLY_MOVED.CS,
                        changes={
                            "amount": {"old": str(old_amount), "new": str(item.amount)}
                        },
                    )

        else:
            existing_of_the_same_type = new_location.items.filter(
                stock_product=item.stock_product, tracking_level=TrackingLevel.FUNGIBLE
            ).first()
            if existing_of_the_same_type:
                existing_of_the_same_type.amount += amount
                existing_of_the_same_type.save()
                if amount == item.amount:
                    item.delete()
                    movement_item = existing_of_the_same_type
                else:
                    item.amount -= amount
                    item.save()
                    movement_item = item
            else:
                movement_item = item
                if amount == item.amount:
                    item.location = new_location
                    item.save()
                else:
                    old_amount = item.amount
                    item.amount -= amount
                    item.save()
                    new_item = WarehouseItem.objects.create(
                        stock_product=item.stock_product,
                        tracking_level=item.tracking_level,
                        amount=amount,
                        location=new_location,
                    )
                    audit_service.add_entry(
                        new_item,
                        action=AuditAction.CREATE,
                        user=context.user_id,
                        reason=AuditMessages.ITEM_CREATED_BY_PARTIAL_MOVE.CS,
                        changes={
                            "amount": {"old": str(old_amount), "new": str(item.amount)}
                        },
                    )
                    audit_service.add_entry(
                        item,
                        action=AuditAction.UPDATE,
                        user=context.user_id,
                        reason=AuditMessages.ITEM_PARTIALLY_MOVED.CS,
                        changes={
                            "amount": {"old": str(old_amount), "new": str(item.amount)}
                        },
                    )

        if movement_item:
            WarehouseMovement.objects.create(
                location_from=location_from,
                location_to=new_location,
                inbound_order_code=item.order_in,
                stock_product=item.stock_product,
                amount=amount,
                item=movement_item,
                batch=movement_batch,
                worker=User.objects.get(pk=context.user_id)
                if context.user_id
                else None,
            )


movement_service = MovementService()


class WarehouseService:
    @staticmethod
    def get_warehouse_item(item_id: int) -> WarehouseItemSchema:
        try:
            item = WarehouseItem.objects.select_related(
                "stock_product",
                "stock_product__unit_of_measure",
                "stock_product__type",
                "stock_product__group",
                "location",
                "location__warehouse",
                "order_in",
                "package_type",
                "package_type__unit_of_measure",
                "batch",
            ).get(pk=item_id)
        except WarehouseItem.DoesNotExist as exc:
            raise WarehouseItemNotFoundError(
                f"Warehouse item with id '{item_id}' does not exist"
            ) from exc

        return warehouse_item_orm_to_schema(item)

    @staticmethod
    def get_warehouse_item_detail(item_id: int) -> WarehouseItemDetailSchema:
        try:
            item = WarehouseItem.objects.select_related(
                "stock_product",
                "stock_product__unit_of_measure",
                "stock_product__type",
                "stock_product__group",
                "location",
                "location__warehouse",
                "order_in",
                "package_type",
                "package_type__unit_of_measure",
                "batch",
            ).get(pk=item_id)
        except WarehouseItem.DoesNotExist as exc:
            raise WarehouseItemNotFoundError(
                f"Warehouse item with id '{item_id}' does not exist"
            ) from exc

        item_schema = warehouse_item_orm_to_schema(item)
        audit_entries = audit_service.get_timeline_for_object(item)

        return WarehouseItemDetailSchema(
            **item_schema.model_dump(),
            audits=[
                AuditTimelineEntrySchema(**entry.model_dump())
                for entry in audit_entries
            ],
        )

    @staticmethod
    def create_warehouse_movement(
        item_id: int, warehouse_order_code: str, new_location_code: str
    ) -> None:
        warehouse_order = InboundWarehouseOrder.objects.get(code=warehouse_order_code)
        item = warehouse_order.items.get(pk=item_id)
        new_location = WarehouseLocation.objects.get(code=new_location_code)

        movement_data = dict(
            location_from=item.location,
            location_to=new_location,
            inbound_order_code=warehouse_order,
            stock_product=item.stock_product,
            amount=item.amount,
            item=None,
            batch=None,
        )

        if item.tracking_level == TrackingLevel.FUNGIBLE:
            movement_data["item"] = None
            movement_data["batch"] = None
        elif item.tracking_level == TrackingLevel.BATCH:
            movement_data["item"] = None
            movement_data["batch"] = item.batch
        elif item.tracking_level in (
            TrackingLevel.SERIALIZED_PIECE,
            TrackingLevel.SERIALIZED_PACKAGE,
        ):
            movement_data["item"] = item
            movement_data["batch"] = None

        WarehouseMovement.objects.create(**movement_data)

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
                "order__items",
                "warehouse_movements",
                "warehouse_movements__location_from",
                "warehouse_movements__location_to",
                "warehouse_movements__stock_product",
            )
            .select_related("order", "order__credit_note")
            .get(code=code)
        )
        return warehouse_inbound_order_orm_to_schema(order)

    @staticmethod
    def create_inbound_order(
        params: WarehouseOrderCreateSchema, context: RequestContext
    ) -> InboundWarehouseOrderSchema:
        purchase_order = InboundOrder.objects.get(code=params.purchase_order_code)
        location = WarehouseLocation.objects.get(code=params.location_code)

        code = WarehouseService.generate_next_inbound_order_code()

        with transaction.atomic():
            warehouse_order = InboundWarehouseOrder.objects.create(
                code=code, order=purchase_order
            )
            audit_service.add_entry(
                warehouse_order,
                action=AuditAction.CREATE,
                user=context.user_id,
                reason=AuditMessages.WAREHOUSE_ORDER_BOUND_TO_PURCHASE_ORDER.CS.format(
                    purchase_order_code=params.purchase_order_code
                ),
            )
            for purchase_item in purchase_order.items.all():
                item = WarehouseItem.objects.create(
                    stock_product=purchase_item.stock_product,
                    tracking_level=TrackingLevel.FUNGIBLE,
                    amount=purchase_item.amount,
                    order_in=warehouse_order,
                    location=location,
                )
                audit_service.add_entry(
                    item,
                    action=AuditAction.CREATE,
                    user=context.user_id,
                    reason=AuditMessages.ORDER_CODE_REFERENCE.CS.format(
                        order_code=warehouse_order.code
                    ),
                )

            inbound_orders_service.transition_order(
                purchase_order.code, InboundOrderState.RECEIVING, context=context
            )

        warehouse_order.refresh_from_db()
        return warehouse_inbound_order_orm_to_schema(warehouse_order)

    @staticmethod
    def get_warehouse_availability(stock_product_code: str) -> Decimal:
        return WarehouseItem.available.filter(
            stock_product__code=stock_product_code
        ).total_amount()
        # .aggregate(total_amount=Sum("amount"))
        # .get("total_amount")
        # or 0.0

    @classmethod
    def get_total_availability(
        cls, stock_product_code: str
    ) -> ProductWarehouseAvailability:
        warehouse_amount = cls.get_warehouse_availability(stock_product_code)
        # warehouse_amount = float(
        #     WarehouseItem.objects.filter(
        #         stock_product__code=stock_product_code, location__is_putaway=False
        #     )
        #     .aggregate(total_amount=Sum("amount"))
        #     .get("total_amount")
        #     or 0.0
        # )

        # todo: pending outcoming orders
        out_amount = Decimal("0")

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

        if package.amount == 0:
            num_of_packages = 1
            package_amount_in_product_uom = amount

        else:
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
                    tracking_level=TrackingLevel.SERIALIZED_PACKAGE,
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
    def preview_batching(
        warehouse_item_id: int,
        product_code: str,
        amount: float,
        batch_code: str | None = None,
    ) -> list[WarehouseItemSchema]:
        warehouse_item = WarehouseItem.objects.get(pk=warehouse_item_id)
        product = StockProduct.objects.get(code=product_code)

        if batch_code:
            barcode = Barcode.objects.get(code=batch_code)
            if barcode.content_type != "Batch":
                raise_by_code(
                    ErrorCode.INVALID_BARCODE,
                    f"Invalid barcode type, {type(barcode.content_object)}, expected Batch",
                )

        items = [
            WarehouseItemSchema(
                id=-1,
                tracking_level=TrackingLevel.BATCH,
                product=product_orm_to_schema(product),
                unit_of_measure=product.unit_of_measure.name,
                amount=float(amount),
                package=None,
                batch=BatchSchema(
                    id=-1,
                    primary_barcode=BarcodeSchema(
                        code=batch_code or "autogen-batch-01234",
                        barcode_type=BarcodeType.EAN13,
                        is_primary=True,
                        changed=timezone.now(),
                        created=timezone.now(),
                    ),
                    changed=timezone.now(),
                    created=timezone.now(),
                ),
                location=location_orm_to_schema(warehouse_item.location),
                created=timezone.now(),
                changed=timezone.now(),
            )
        ]

        return items

    @staticmethod
    def preview_serial_tracking(
        warehouse_item_id: int,
        product_code: str,
        amount: float,
    ) -> list[WarehouseItemSchema]:
        warehouse_item = WarehouseItem.objects.get(pk=warehouse_item_id)
        product = StockProduct.objects.get(code=product_code)

        requested_amount = Decimal(str(amount))
        if requested_amount <= 0 or requested_amount % 1 != 0:
            raise_by_code(
                ErrorCode.INVALID_CONVERSION,
                f"Amount '{amount}' ({product.unit_of_measure.name}) must be a positive whole number for serial tracking preview.",
            )

        num_of_items = int(requested_amount)

        items = [
            WarehouseItemSchema(
                id=-1,
                tracking_level=TrackingLevel.SERIALIZED_PIECE,
                product=product_orm_to_schema(product),
                unit_of_measure=product.unit_of_measure.name,
                amount=1.0,
                package=None,
                batch=None,
                primary_barcode=generate_warehouse_item_code(),
                location=location_orm_to_schema(warehouse_item.location),
                created=timezone.now(),
                changed=timezone.now(),
            )
            for _ in range(num_of_items)
        ]

        return items

    @staticmethod
    def add_or_remove_inbound_order_items(
        order_code: str,
        to_be_removed: list[WarehouseItemSchema],
        to_be_added: list[WarehouseItemSchema],
        context: RequestContext,
    ) -> InboundWarehouseOrderSchema:
        order = InboundWarehouseOrder.objects.get(code=order_code)

        raise_if_readonly(order)

        try:
            with transaction.atomic():
                for item in to_be_removed:
                    order.items.get(pk=item.id).delete()
                for item in to_be_added:
                    new_item = WarehouseItem.objects.create(
                        order_in=order,
                        package_type=PackageType.objects.get(name=item.package.type)
                        if item.package
                        else None,
                        stock_product=StockProduct.objects.get(code=item.product.code),
                        amount=item.amount,
                        location=WarehouseLocation.objects.get(code=item.location.code),
                    )
                    audit_service.add_entry(
                        new_item,
                        action=AuditAction.CREATE,
                        user=context.user_id,
                        reason=AuditMessages.ORDER_CODE_REFERENCE.CS.format(
                            order_code=order_code
                        ),
                    )
        except ObjectDoesNotExist as exc:
            raise WarehouseItemBadRequestError(str(exc))

        return warehouse_inbound_order_orm_to_schema(
            InboundWarehouseOrder.objects.get(code=order_code)
        )

    @staticmethod
    def setup_tracking_for_inbound_order_item(
        order_code: str,
        stock_product_code: str,
        to_be_added: list[WarehouseItemSchema],
        context: RequestContext,
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
            stock_product__code=stock_product_code,
            order_in=order,
            tracking_level=TrackingLevel.FUNGIBLE,
        )

        remaining_amount = untracked_item.amount - Decimal(
            sum(item.amount for item in to_be_added)
        )
        try:
            with transaction.atomic():
                for new_item in to_be_added:
                    batch = None
                    if new_item.batch and new_item.batch.primary_barcode:
                        batch, _ = get_or_create_batch(
                            new_item.batch.primary_barcode.code
                        )

                    item = WarehouseItem.objects.create(
                        order_in=order,
                        package_type=PackageType.objects.get(name=new_item.package.type)
                        if new_item.package
                        else None,
                        batch=batch,
                        # todo: code=generate_warehouse_item_code(),
                        stock_product=StockProduct.objects.get(
                            code=new_item.product.code
                        ),
                        amount=new_item.amount,
                        location=WarehouseLocation.objects.get(
                            code=new_item.location.code
                        ),
                        tracking_level=new_item.tracking_level,
                    )
                    item.attach_barcode(
                        code=generate_warehouse_item_code(), is_primary=True
                    )
                    audit_service.add_entry(
                        item,
                        action=AuditAction.CREATE,
                        user=context.user_id,
                        reason=AuditMessages.TRACKING_SETUP.CS.format(
                            order_code=order_code,
                            tracking_level=new_item.tracking_level,
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
        warehouse_item_id: int,
    ) -> InboundWarehouseOrderSchema:
        order = InboundWarehouseOrder.objects.get(code=order_code)

        raise_if_readonly(order)

        item = WarehouseItem.objects.get(pk=warehouse_item_id, order_in=order)
        if not item:
            raise WarehouseItemNotFoundError(
                f"No warehouse item with pk={warehouse_item_id} in order '{order.code}'"
            )

        existing_not_packaged = order.items.filter(
            stock_product=item.stock_product,
            package_type__isnull=True,
            tracking_level=TrackingLevel.FUNGIBLE,
        ).first()
        try:
            with transaction.atomic():
                if not existing_not_packaged:
                    WarehouseItem.objects.create(
                        stock_product=item.stock_product,
                        location=item.location,
                        amount=item.amount,
                        order_in=order,
                        tracking_level=TrackingLevel.FUNGIBLE,
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
        code: str,
        body: InboundWarehouseOrderUpdateSchema,
        context: RequestContext,
        no_audit: bool = False,
    ) -> None:
        with transaction.atomic():
            order = InboundWarehouseOrder.objects.get(code=code)
            old_state = order.state
            order.state = body.state
            order.save()
            if not no_audit:
                audit_service.add_entry(
                    order,
                    user=context.user_id,
                    action=AuditAction.UPDATE,
                    reason=AuditMessages.WAREHOUSE_ORDER_UPDATED.CS,
                    changes={"state": {"old": old_state, "new": body.state}},
                )
        return None

    @classmethod
    def transition_order(
        cls, code: str, state: InboundWarehouseOrderState, context: RequestContext
    ) -> None:
        order = InboundWarehouseOrder.objects.get(code=code)
        old_state = order.state
        cls.update_inbound_order(
            code,
            InboundWarehouseOrderUpdateSchema(state=state),
            context=context,
            no_audit=True,
        )

        if old_state != state:
            audit_service.add_entry(
                order,
                user=context.user_id,
                action=AuditAction.TRANSITION,
                reason=AuditMessages.WAREHOUSE_ORDER_STATE_CHANGED.CS.format(
                    old_state=old_state, new_state=state
                ),
                changes={"state": {"old": old_state, "new": state}},
            )

        return None

    @classmethod
    def remove_from_order_to_credit_note(
        cls,
        warehouse_order_code: str,
        warehouse_item_id: int,
        amount: float | Decimal,
        context: RequestContext,
    ) -> InboundWarehouseOrderSchema:
        amount = Decimal(amount)
        warehouse_item = WarehouseItem.objects.prefetch_related("stock_product").get(
            pk=warehouse_item_id
        )
        stock_product = warehouse_item.stock_product
        warehouse_order = InboundWarehouseOrder.objects.get(code=warehouse_order_code)
        order = warehouse_order.order

        order_item = InboundOrderItem.objects.filter(
            order=order, stock_product=stock_product
        ).get()
        if warehouse_order.state != InboundWarehouseOrderState.DRAFT:
            raise WarehouseGenericError(
                f"Warehouse order '{warehouse_order.code}' is already confirmed and read-only."
            )

        with transaction.atomic():
            if amount > warehouse_item.amount:
                raise WarehouseGenericError(
                    f"Requested amount ({amount}) exceeds item amount: {warehouse_item.amount} ({warehouse_item.stock_product.name})"
                )

            note, created = inbound_orders_service.get_or_create_credit_note(
                order.code, context
            )
            if note.state != CreditNoteState.DRAFT:
                raise WarehouseGenericError(
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

            if created:
                audit_service.add_entry(
                    warehouse_order,
                    user=context.user_id,
                    action=AuditAction.CREATE,
                    reason=AuditMessages.CREDIT_NOTE_CREATED.CS,
                    changes={"credit_note": {"new": note.code}},
                )
            audit_service.add_entry(
                warehouse_order,
                user=context.user_id,
                action=AuditAction.OTHER,
                reason=AuditMessages.ITEM_DISCARDED_TO_CREDIT_NOTE.CS,
                changes={
                    "credit_note": note.code,
                    "stock_product": stock_product.name,
                    "amount": str(amount),
                },
            )

        return cls.get_inbound_warehouse_order(warehouse_order_code)

    @classmethod
    def confirm_draft(cls, code: str, context: RequestContext) -> None:
        w_order = cls.get_inbound_warehouse_order(code)
        if w_order.state != InboundWarehouseOrderState.DRAFT:
            raise WarehouseGenericError(
                f"Warehouse order '{code}' (state={w_order.state}) has to be in draft state in order to be confirmed."
            )
        cls.transition_order(code, InboundWarehouseOrderState.PENDING, context)
        inbound_order = InboundOrder.objects.get(warehouse_orders__code=code)
        inbound_orders_service.transition_order(
            inbound_order.code, InboundOrderState.PUTAWAY, context=context
        )
        if credit_note := getattr(inbound_order, "credit_note", None):
            inbound_orders_service.transition_credit_note(
                credit_note.code,
                CreditNoteState.CONFIRMED,
                context=context,
            )

    @classmethod
    def reset_to_draft(cls, code: str, context: RequestContext) -> None:
        w_order = cls.get_inbound_warehouse_order(code)
        if w_order.state != InboundWarehouseOrderState.PENDING:
            raise WarehouseGenericError(
                f"Warehouse order ${code}, state={w_order.state} has to be in pending state in order to be reset to draft."
            )
        cls.transition_order(code, InboundWarehouseOrderState.DRAFT, context)
        inbound_order = InboundOrder.objects.get(warehouse_orders__code=code)
        inbound_orders_service.transition_order(
            inbound_order.code, InboundOrderState.RECEIVING, context=context
        )
        if credit_note := getattr(inbound_order, "credit_note", None):
            inbound_orders_service.transition_credit_note(
                credit_note.code, CreditNoteState.DRAFT, context=context
            )

    @staticmethod
    def recalculate_average_purchase_price(
        product_code: str, amount: Decimal, unit_price: Decimal, context: RequestContext
    ) -> None:
        stock_product = StockProduct.objects.get(code=product_code)
        old_purchase_price = stock_product.purchase_price
        # item_from_order = item.order_in.order.items.filter(
        #     stock_product=stock_product
        # ).first()
        # if not item_from_order:
        #     raise WarehouseGenericError(
        #         f"Warehouse item lacks an appropriate order item ({stock_product.name} - {stock_product.code})"
        #     )
        # unit_price = item_from_order.unit_price
        total_items_amount = Decimal("0.0")
        if not stock_product.purchase_price:
            stock_product.purchase_price = unit_price
        else:
            total_items_amount = WarehouseItem.available.total_amount(product_code)
            if not total_items_amount:
                new_avg = unit_price
            else:
                total_price = (
                    total_items_amount * stock_product.purchase_price
                    + Decimal(amount) * Decimal(unit_price)
                )
                total_amount = total_items_amount + amount
                new_avg = total_price / total_amount
            stock_product.purchase_price = new_avg

        stock_product.save()

        audit_service.add_entry(
            stock_product,
            user=context.user_id,
            action=AuditAction.UPDATE,
            reason=AuditMessages.AVERAGE_PURCHASE_PRICE_RECALCULATED.CS,
            changes={
                "purchase_price": {
                    "old": str(old_purchase_price)
                    if old_purchase_price is not None
                    else None,
                    "new": str(stock_product.purchase_price)
                    if stock_product.purchase_price is not None
                    else None,
                },
                "amount": {
                    "old": str(total_items_amount),
                    "new": str(total_items_amount + amount),
                },
            },
        )

    @classmethod
    def putaway_item(
        cls,
        item_id: int,
        warehouse_order_code: str,
        new_location_code: str,
        context: RequestContext,
    ) -> None:
        """
        Putaway an item while processing an inbound order.
        """
        warehouse_order = InboundWarehouseOrder.objects.get(code=warehouse_order_code)
        if warehouse_order.state == InboundWarehouseOrderState.DRAFT:
            raise WarehouseGenericError(
                f"Warehouse order '{warehouse_order_code}' is not yet confirmed and thus read-only."
            )

        if warehouse_order.state in (
            InboundWarehouseOrderState.COMPLETED,
            InboundWarehouseOrderState.CANCELLED,
        ):
            raise WarehouseGenericError(
                f"Warehouse order ${warehouse_order_code} is already confirmed and/or canceled and thus read-only."
            )

        item = warehouse_order.items.get(pk=item_id)
        new_location = WarehouseLocation.objects.get(code=new_location_code)

        with transaction.atomic():
            amount = item.amount
            if not item.order_in:
                raise ValueError()
            unit_price = item.order_in.order.items.get(
                stock_product=item.stock_product
            ).unit_price
            cls.recalculate_average_purchase_price(
                item.stock_product.code, amount, unit_price, context=context
            )

            movement_service.move_item(item, context, new_location)

            if warehouse_order.items.filter(location__is_putaway=True).count() == 0:
                cls.transition_order(
                    warehouse_order_code,
                    InboundWarehouseOrderState.COMPLETED,
                    context=context,
                )
                if (
                    warehouse_order.order.warehouse_orders.exclude(
                        state=InboundWarehouseOrderState.COMPLETED
                    ).count()
                    == 0
                ):
                    inbound_orders_service.transition_order(
                        warehouse_order.order.code,
                        InboundOrderState.COMPLETED,
                        context=context,
                    )
            else:
                cls.transition_order(
                    warehouse_order_code,
                    InboundWarehouseOrderState.STARTED,
                    context=context,
                )

    # @staticmethod
    # def move_item(
    #     item_code: str, location_code: str | None = None, amount: float = None
    # ) -> None:
    #     pass

    @classmethod
    def create_child_warehouse_order(
        cls,
        parent_code: str,
        context: RequestContext,
    ) -> InboundWarehouseOrder:
        parent_order = InboundWarehouseOrder.objects.select_related("order").get(
            code=parent_code
        )
        child_code = cls.generate_next_inbound_order_code()
        with transaction.atomic():
            child_order = InboundWarehouseOrder.objects.create(
                code=child_code,
                order=parent_order.order,
                primary_order=parent_order,
                state=InboundWarehouseOrderState.DRAFT,
            )
            audit_service.add_entry(
                child_order,
                action=AuditAction.CREATE,
                user=context.user_id,
                reason=AuditMessages.CHILD_WAREHOUSE_ORDER_CREATED.CS.format(
                    child_code=child_code,
                    parent_code=parent_code,
                ),
                changes={"parent_order": parent_code},
            )
            audit_service.add_entry(
                parent_order,
                action=AuditAction.OTHER,
                user=context.user_id,
                reason=AuditMessages.CHILD_WAREHOUSE_ORDER_CREATED.CS.format(
                    child_code=child_code,
                    parent_code=parent_code,
                ),
                changes={"child_order": child_code},
            )
        return child_order

    @classmethod
    def offload_items_to_child_order(
        cls,
        parent_code: str,
        items: list[tuple[int, Decimal]],
        context: RequestContext,
    ) -> InboundWarehouseOrderSchema:
        """
        Move a list of (item_id, amount) pairs from the parent warehouse order
        into a child order.  A new child order is created automatically if none
        exists yet.
        """
        parent_order = InboundWarehouseOrder.objects.select_related("order").get(
            code=parent_code
        )

        existing_child = parent_order.derived_orders.filter(
            state=InboundWarehouseOrderState.DRAFT
        ).first()
        child_order = existing_child or cls.create_child_warehouse_order(
            parent_code, context
        )

        with transaction.atomic():
            for item_id, amount in items:
                amount = Decimal(str(amount))
                item = parent_order.items.select_related(
                    "stock_product", "location", "batch", "package_type"
                ).get(pk=item_id)

                if amount > item.amount:
                    raise WarehouseGenericError(
                        f"Requested offload amount ({amount}) exceeds item amount "
                        f"({item.amount}) for item id={item_id}."
                    )

                if amount == item.amount:
                    item.order_in = child_order
                    item.save()
                    offloaded_item = item
                else:
                    item.amount -= amount
                    item.save()
                    offloaded_item = WarehouseItem.objects.create(
                        stock_product=item.stock_product,
                        tracking_level=item.tracking_level,
                        amount=amount,
                        location=item.location,
                        order_in=child_order,
                        batch=item.batch,
                        package_type=item.package_type,
                    )

                audit_service.add_entry(
                    offloaded_item,
                    action=AuditAction.UPDATE,
                    user=context.user_id,
                    reason=AuditMessages.ITEM_OFFLOADED_TO_CHILD_ORDER.CS.format(
                        amount=amount,
                        child_code=child_order.code,
                    ),
                    changes={
                        "order_in": {"old": parent_code, "new": child_order.code},
                        "amount": str(amount),
                    },
                )
                audit_service.add_entry(
                    parent_order,
                    action=AuditAction.OTHER,
                    user=context.user_id,
                    reason=AuditMessages.ITEM_OFFLOADED_TO_CHILD_ORDER.CS.format(
                        amount=amount,
                        child_code=child_order.code,
                    ),
                    changes={
                        "item_id": item_id,
                        "amount": str(amount),
                        "child_order": child_order.code,
                    },
                )

        return cls.get_inbound_warehouse_order(parent_code)


warehouse_service = WarehouseService()
