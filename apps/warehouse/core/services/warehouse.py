import uuid
from decimal import Decimal
from typing import cast

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import QuerySet, Sum
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
    OutboundWarehouseOrderSchema,
    ProductWarehouseAvailability,
    WarehouseItemDetailSchema,
    WarehouseItemSchema,
    InboundWarehouseOrderUpdateSchema,
    BatchSchema,
    DraftItemAddSchema,
    BarcodeLookupResponse,
    MoveItemRequest,
)
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.manufacturing import manufacturing_orders_service
from apps.warehouse.core.services.orders import inbound_orders_service
from apps.warehouse.core.services.outbound_orders import outbound_orders_service
from apps.warehouse.core.services.warehouse_order_factory import (
    WarehouseOrderKind,
    create_warehouse_order,
)
from apps.warehouse.core.transformation import (
    warehouse_inbound_order_orm_to_schema,
    warehouse_outbound_order_orm_to_schema,
    product_orm_to_schema,
    package_orm_to_schema,
    location_orm_to_schema,
    warehouse_item_orm_to_schema,
    batch_orm_to_schema,
)
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.barcode import BarcodeType, Barcode
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderState,
    OutboundOrderState,
    CreditNoteState,
    CreditNoteToSupplier,
    CreditNoteToSupplierItem,
)
from apps.warehouse.models.packaging import PackageType
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    InboundWarehouseOrderItem,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderItem,
    WarehouseItem,
    WarehouseMovement,
    WarehouseLocation,
    InboundWarehouseOrderState,
    OutboundWarehouseOrderState,
    TrackingLevel,
    Batch,
)


def generate_warehouse_item_code() -> str:
    return str(uuid.uuid4())[:13]


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
        # Wrap entire function in atomic transaction for consistency
        with transaction.atomic():
            location_from = item.location
            amount = amount or item.amount
            if isinstance(new_location_or_code, str):
                new_location = WarehouseLocation.objects.get(code=new_location_or_code)
            else:
                new_location = new_location_or_code

            movement_item = None
            movement_batch = None
            existing_of_the_same_batch = None

            if item.tracking_level in (
                TrackingLevel.SERIALIZED_PACKAGE,
                TrackingLevel.SERIALIZED_PIECE,
            ):
                item.location = new_location
                item.save()
                movement_item = item

            elif item.tracking_level == TrackingLevel.BATCH:
                movement_batch = item.batch
                # Lock merge target to prevent concurrent modifications
                existing_of_the_same_batch = (
                    WarehouseItem.physical_stock.select_for_update()
                    .filter(location=new_location, batch=item.batch)
                    .first()
                )
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
                                "amount": {
                                    "old": str(old_amount),
                                    "new": str(item.amount),
                                }
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
                                "amount": {
                                    "old": str(old_amount),
                                    "new": str(item.amount),
                                }
                            },
                        )
                        audit_service.add_entry(
                            item,
                            action=AuditAction.UPDATE,
                            user=context.user_id,
                            reason=AuditMessages.ITEM_PARTIALLY_MOVED.CS,
                            changes={
                                "amount": {
                                    "old": str(old_amount),
                                    "new": str(item.amount),
                                }
                            },
                        )

            else:
                # Lock merge target to prevent concurrent modifications (FUNGIBLE branch)
                existing_of_the_same_type = (
                    WarehouseItem.physical_stock.select_for_update()
                    .filter(
                        location=new_location,
                        stock_product=item.stock_product,
                        tracking_level=TrackingLevel.FUNGIBLE,
                    )
                    .first()
                )
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
                        # Fix bug #5: propagate order_in, source_order_item, batch, package_type
                        new_item = WarehouseItem.objects.create(
                            stock_product=item.stock_product,
                            tracking_level=item.tracking_level,
                            amount=amount,
                            location=new_location,
                            order_in=item.order_in,
                            source_order_item=item.source_order_item,
                            batch=item.batch,
                            package_type=item.package_type,
                        )
                        audit_service.add_entry(
                            new_item,
                            action=AuditAction.CREATE,
                            user=context.user_id,
                            reason=AuditMessages.ITEM_CREATED_BY_PARTIAL_MOVE.CS,
                            changes={
                                "amount": {
                                    "old": str(old_amount),
                                    "new": str(item.amount),
                                }
                            },
                        )
                        audit_service.add_entry(
                            item,
                            action=AuditAction.UPDATE,
                            user=context.user_id,
                            reason=AuditMessages.ITEM_PARTIALLY_MOVED.CS,
                            changes={
                                "amount": {
                                    "old": str(old_amount),
                                    "new": str(item.amount),
                                }
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
                "outbound_assignment__warehouse_order",
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
    def barcode_lookup(
        barcode: str, product_code: str | None = None
    ) -> BarcodeLookupResponse:
        """
        Look up a barcode and identify what entity it represents.
        Returns details about the scanned entity and matching warehouse items if applicable.
        """
        # Try to find the barcode in the database
        barcode_obj = (
            Barcode.objects.select_related("content_type").filter(code=barcode).first()
        )

        if not barcode_obj:
            return BarcodeLookupResponse(
                found=False,
                entity_type=None,
                warehouse_item=None,
                batch=None,
                location=None,
                product=None,
                matching_items=None,
            )

        # Determine what type of entity this barcode points to
        content_type = barcode_obj.content_type
        model_class = content_type.model_class()

        if not model_class:
            return BarcodeLookupResponse(
                found=False,
                entity_type=None,
                warehouse_item=None,
                batch=None,
                location=None,
                product=None,
                matching_items=None,
            )

        # Fetch the actual object
        entity = model_class.objects.filter(pk=barcode_obj.object_id).first()  # type: ignore[attr-defined]

        if not entity:
            return BarcodeLookupResponse(
                found=False,
                entity_type=None,
                warehouse_item=None,
                batch=None,
                location=None,
                product=None,
                matching_items=None,
            )

        # Build response based on entity type
        response = BarcodeLookupResponse(
            found=True,
            entity_type=None,
            warehouse_item=None,
            batch=None,
            location=None,
            product=None,
            matching_items=None,
        )

        if isinstance(entity, WarehouseItem):
            # Check if item is already assigned to an outbound order
            item = (
                WarehouseItem.physical_stock.select_related(
                    "stock_product",
                    "stock_product__unit_of_measure",
                    "location",
                    "location__warehouse",
                    "batch",
                    "package_type",
                    "package_type__unit_of_measure",
                )
                .filter(pk=entity.pk)
                .first()
            )
            if item:
                response.entity_type = "warehouse_item"
                response.warehouse_item = warehouse_item_orm_to_schema(item)
            else:
                # Item is already assigned or doesn't exist in physical stock
                return BarcodeLookupResponse(
                    found=False,
                    entity_type=None,
                    warehouse_item=None,
                    batch=None,
                    location=None,
                    product=None,
                    matching_items=None,
                )

        elif isinstance(entity, Batch):
            response.entity_type = "batch"
            response.batch = batch_orm_to_schema(entity)

            # Find matching warehouse items with this batch (use physical_stock to include putaway)
            items_qs = WarehouseItem.physical_stock.select_related(
                "stock_product",
                "stock_product__unit_of_measure",
                "location",
                "location__warehouse",
                "batch",
                "package_type",
                "package_type__unit_of_measure",
            ).filter(batch=entity)

            if product_code:
                items_qs = items_qs.filter(stock_product__code=product_code)

            response.matching_items = [
                warehouse_item_orm_to_schema(item) for item in items_qs[:20]
            ]

        elif isinstance(entity, WarehouseLocation):
            response.entity_type = "location"
            response.location = location_orm_to_schema(entity)

            # Find available warehouse items at this location (use physical_stock to include putaway)
            items_qs = WarehouseItem.physical_stock.select_related(
                "stock_product",
                "stock_product__unit_of_measure",
                "location",
                "location__warehouse",
                "batch",
                "package_type",
                "package_type__unit_of_measure",
            ).filter(location=entity)

            if product_code:
                items_qs = items_qs.filter(stock_product__code=product_code)

            response.matching_items = [
                warehouse_item_orm_to_schema(item) for item in items_qs[:20]
            ]

        elif isinstance(entity, StockProduct):
            response.entity_type = "product"
            response.product = product_orm_to_schema(entity)

            # Find available warehouse items of this product (use physical_stock to include putaway)
            items_qs = WarehouseItem.physical_stock.select_related(
                "stock_product",
                "stock_product__unit_of_measure",
                "location",
                "location__warehouse",
                "batch",
                "package_type",
                "package_type__unit_of_measure",
            ).filter(stock_product=entity)

            response.matching_items = [
                warehouse_item_orm_to_schema(item) for item in items_qs[:20]
            ]

        return response

    @staticmethod
    def create_warehouse_movement(
        item_id: int, warehouse_order_code: str, new_location_code: str
    ) -> None:
        warehouse_order = InboundWarehouseOrder.objects.get(code=warehouse_order_code)
        item = warehouse_order.items.get(pk=item_id)
        new_location = WarehouseLocation.objects.get(code=new_location_code)

        movement_data: dict[str, object] = dict(
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
    def get_inbound_warehouse_order(code: str):
        order = WarehouseService.get_inbound_warehouse_order_model(code)
        return warehouse_inbound_order_orm_to_schema(order)

    @staticmethod
    def get_inbound_warehouse_order_model(code: str) -> InboundWarehouseOrder:
        order = (
            InboundWarehouseOrder.objects.prefetch_related(
                "order_items",
                "order_items__stock_product",
                "order_items__stock_product__unit_of_measure",
                "order_items__package_type",
                "order_items__warehouse_items",
                "order_items__warehouse_items__location",
                "order_items__warehouse_items__outbound_assignment",
                "order_items__warehouse_items__outbound_assignment__warehouse_order",
                "items",
                "items__stock_product",
                "items__stock_product__unit_of_measure",
                "order__items",
                "warehouse_movements",
                "warehouse_movements__location_from",
                "warehouse_movements__location_to",
                "warehouse_movements__stock_product",
            )
            .select_related("order", "order__credit_note", "pickup_location")
            .get(code=code)
        )
        return order

    @staticmethod
    def get_outbound_warehouse_order(code: str) -> OutboundWarehouseOrderSchema:
        order = WarehouseService.get_outbound_warehouse_order_model(code)
        return warehouse_outbound_order_orm_to_schema(order)

    @staticmethod
    def get_outbound_warehouse_order_model(code: str) -> OutboundWarehouseOrder:
        return (
            OutboundWarehouseOrder.objects.select_related(
                "order",
                "order__customer",
                "primary_order",
                "primary_order__order",
            )
            .prefetch_related(
                "order__items",
                "order__warehouse_orders",
                "derived_orders",
                "order_items",
                "order_items__stock_product",
                "order_items__stock_product__unit_of_measure",
                "order_items__desired_package_type",
                "order_items__desired_batch",
                "order_items__warehouse_item",
                "order_items__warehouse_item__stock_product",
                "order_items__warehouse_item__stock_product__unit_of_measure",
                "order_items__warehouse_item__location",
                "order_items__warehouse_item__location__warehouse",
                "order_items__warehouse_item__package_type",
                "order_items__warehouse_item__package_type__unit_of_measure",
                "order_items__warehouse_item__batch",
                "warehouse_movements",
                "warehouse_movements__location_from",
                "warehouse_movements__location_to",
                "warehouse_movements__stock_product",
                "warehouse_movements__item",
            )
            .get(code=code)
        )

    @staticmethod
    def _get_outbound_item_candidates_qs(
        order_item: OutboundWarehouseOrderItem,
    ) -> QuerySet[WarehouseItem]:
        queryset = WarehouseItem.physical_stock.filter(
            stock_product=order_item.stock_product,
        )
        if order_item.desired_package_type is not None:
            queryset = queryset.filter(package_type=order_item.desired_package_type)
        if order_item.desired_batch is not None:
            queryset = queryset.filter(batch=order_item.desired_batch)
        return queryset.order_by("created", "pk")

    @classmethod
    def get_outbound_item_candidates(
        cls,
        warehouse_order_code: str,
        order_item_id: int,
    ) -> list[WarehouseItemSchema]:
        warehouse_order = cls.get_outbound_warehouse_order_model(warehouse_order_code)
        order_item = warehouse_order.order_items.select_related(
            "stock_product",
            "desired_package_type",
            "desired_batch",
        ).get(pk=order_item_id)

        candidates = cls._get_outbound_item_candidates_qs(order_item).select_related(
            "stock_product",
            "stock_product__unit_of_measure",
            "location",
            "location__warehouse",
            "package_type",
            "package_type__unit_of_measure",
            "batch",
        )
        return [warehouse_item_orm_to_schema(item) for item in candidates]

    @staticmethod
    def _split_outbound_pick_item(
        item: WarehouseItem,
        requested_amount: Decimal,
        context: RequestContext,
    ) -> WarehouseItem:
        # Lock the item to prevent concurrent splits
        item = WarehouseItem.objects.select_for_update().get(pk=item.pk)

        if item.amount < requested_amount:
            raise WarehouseGenericError(
                f"Warehouse item '{item.pk}' has insufficient amount ({item.amount} < {requested_amount})."
            )

        if item.amount == requested_amount:
            return item

        if item.tracking_level in (
            TrackingLevel.SERIALIZED_PIECE,
            TrackingLevel.SERIALIZED_PACKAGE,
        ):
            raise WarehouseGenericError(
                f"Serialized warehouse item '{item.pk}' must match requested amount exactly."
            )

        old_amount = item.amount
        item.amount -= requested_amount
        item.save(update_fields=["amount", "changed"])

        new_item = WarehouseItem.objects.create(
            stock_product=item.stock_product,
            tracking_level=item.tracking_level,
            amount=requested_amount,
            location=item.location,
            order_in=item.order_in,
            source_order_item=item.source_order_item,
            batch=item.batch,
            package_type=item.package_type,
        )
        audit_service.add_entry(
            item,
            action=AuditAction.UPDATE,
            user=context.user_id,
            reason=AuditMessages.ITEM_PARTIALLY_MOVED.CS,
            changes={"amount": {"old": str(old_amount), "new": str(item.amount)}},
        )
        audit_service.add_entry(
            new_item,
            action=AuditAction.CREATE,
            user=context.user_id,
            reason=AuditMessages.ITEM_CREATED_BY_PARTIAL_MOVE.CS,
            changes={"amount": {"old": None, "new": str(new_item.amount)}},
        )

        # Write WarehouseMovement for split operation (fix bug #9)
        WarehouseMovement.objects.create(
            location_from=item.location,
            location_to=item.location,  # Same location, split operation
            inbound_order_code=item.order_in,
            stock_product=item.stock_product,
            amount=new_item.amount,
            item=new_item,
            batch=item.batch,
            worker=User.objects.get(pk=context.user_id) if context.user_id else None,
        )

        return new_item

    @staticmethod
    def _unpack_package(
        package_item: WarehouseItem,
        requested_amount: Decimal,
        context: RequestContext,
    ) -> WarehouseItem:
        """Unpack units from a package, creating a new item."""
        # Lock the package to prevent concurrent unpacking
        package_item = WarehouseItem.objects.select_for_update().get(pk=package_item.pk)

        # 1. Check disallow_unpacking
        if package_item.stock_product.disallow_unpacking:
            raise WarehouseGenericError(
                f"Cannot unpack package: Product '{package_item.stock_product.code}' "
                "has unpacking disabled."
            )

        # 2. Reduce package amount
        old_amount = package_item.amount
        package_item.amount -= requested_amount
        package_item.save(update_fields=["amount", "changed"])

        # 3. Determine new tracking level
        new_tracking_level = TrackingLevel.FUNGIBLE

        # 4. Create unpacked item
        unpacked_item = WarehouseItem.objects.create(
            stock_product=package_item.stock_product,
            tracking_level=new_tracking_level,
            amount=requested_amount,
            location=package_item.location,
            order_in=package_item.order_in,
            source_order_item=package_item.source_order_item,
            batch=package_item.batch,
            package_type=None,  # Unpacked items lose package designation
            unpacked_from=package_item,
        )

        # 5. Audit trail
        audit_service.add_entry(
            package_item,
            action=AuditAction.UPDATE,
            user=context.user_id,
            reason=AuditMessages.PACKAGE_UNPACKED.CS.format(
                amount_unpacked=str(requested_amount),
                amount_remaining=str(package_item.amount),
            ),
            changes={
                "amount": {"old": str(old_amount), "new": str(package_item.amount)}
            },
        )
        audit_service.add_entry(
            unpacked_item,
            action=AuditAction.CREATE,
            user=context.user_id,
            reason=AuditMessages.ITEM_CREATED_BY_UNPACKING.CS.format(
                original_item_id=str(package_item.pk)
            ),
        )

        # Write WarehouseMovement for unpack operation (fix bug #9)
        WarehouseMovement.objects.create(
            location_from=package_item.location,
            location_to=package_item.location,  # Same location, unpack operation
            inbound_order_code=package_item.order_in,
            stock_product=unpacked_item.stock_product,
            amount=unpacked_item.amount,
            item=unpacked_item,
            batch=unpacked_item.batch,
            worker=User.objects.get(pk=context.user_id) if context.user_id else None,
        )

        return unpacked_item

    @staticmethod
    def _split_order_item_for_partial_fulfillment(
        order_item: OutboundWarehouseOrderItem,
        available_amount: Decimal,
        context: RequestContext,
    ) -> OutboundWarehouseOrderItem:
        """Split order item when available < requested. Returns new fulfilled item."""
        remaining_amount = order_item.amount - available_amount

        # Update original to hold remaining unfulfilled amount
        old_amount = order_item.amount
        order_item.amount = remaining_amount
        order_item.save(update_fields=["amount", "changed"])

        # Create new item for fulfilled portion
        fulfilled_item = OutboundWarehouseOrderItem.objects.create(
            warehouse_order=order_item.warehouse_order,
            source_order_item=order_item.source_order_item,
            stock_product=order_item.stock_product,
            amount=available_amount,
            desired_package_type=order_item.desired_package_type,
            desired_batch=order_item.desired_batch,
            index=order_item.index,
        )

        # Audit trail
        audit_service.add_entry(
            order_item,
            action=AuditAction.UPDATE,
            user=context.user_id,
            reason=AuditMessages.ORDER_ITEM_SPLIT_FOR_PARTIAL_FULFILLMENT.CS.format(
                fulfilled_amount=str(available_amount),
                remaining_amount=str(remaining_amount),
            ),
            changes={"amount": {"old": str(old_amount), "new": str(remaining_amount)}},
        )
        audit_service.add_entry(
            fulfilled_item,
            action=AuditAction.CREATE,
            user=context.user_id,
            reason=AuditMessages.ORDER_ITEM_SPLIT_FOR_PARTIAL_FULFILLMENT.CS.format(
                fulfilled_amount=str(available_amount),
                remaining_amount=str(remaining_amount),
            ),
        )

        return fulfilled_item

    @staticmethod
    def _handle_outbound_item_assignment_with_splitting(
        warehouse_item: WarehouseItem,
        order_item: OutboundWarehouseOrderItem,
        requested_amount: Decimal,
        context: RequestContext,
    ) -> tuple[WarehouseItem, OutboundWarehouseOrderItem]:
        """
        Handle four scenarios:
        1. User picking partial (requested < order amount): split order item first
        2. Exact match: return as-is
        3. Available > requested: split or unpack warehouse item
        4. Available < requested: partial fulfillment

        Returns: (warehouse_item_to_assign, order_item_to_receive_assignment)
        """
        available_amount = warehouse_item.amount
        is_serialized = warehouse_item.tracking_level in (
            TrackingLevel.SERIALIZED_PIECE,
            TrackingLevel.SERIALIZED_PACKAGE,
        )

        # CRITICAL: If user is intentionally picking less than order requires,
        # split the order item first before handling warehouse item splitting
        final_order_item = order_item
        if requested_amount < order_item.amount:
            # User is picking partial - create a new order item for the fulfilled portion
            final_order_item = (
                WarehouseService._split_order_item_for_partial_fulfillment(
                    order_item, requested_amount, context
                )
            )

        # Now handle warehouse item splitting based on available vs requested
        # Exact match
        if available_amount == requested_amount:
            return (warehouse_item, final_order_item)

        # Available > requested
        elif available_amount > requested_amount:
            if is_serialized:
                # Unpacking scenario
                unpacked_item = WarehouseService._unpack_package(
                    warehouse_item, requested_amount, context
                )
                return (unpacked_item, final_order_item)
            else:
                # Standard split for FUNGIBLE/BATCH
                split_item = WarehouseService._split_outbound_pick_item(
                    warehouse_item, requested_amount, context
                )
                return (split_item, final_order_item)

        # Available < requested
        else:
            if is_serialized:
                # Partial fulfillment: split order item again
                # (This handles the case where warehouse has even less than the partial pick amount)
                doubly_split_item = (
                    WarehouseService._split_order_item_for_partial_fulfillment(
                        final_order_item, available_amount, context
                    )
                )
                return (warehouse_item, doubly_split_item)
            else:
                # Consume entire warehouse item for partial fulfillment
                return (warehouse_item, final_order_item)

    @classmethod
    def _sync_outbound_warehouse_order_state(
        cls,
        warehouse_order: OutboundWarehouseOrder,
        context: RequestContext,
    ) -> None:
        assigned_count = warehouse_order.order_items.filter(
            warehouse_item__isnull=False
        ).count()
        total_count = warehouse_order.order_items.count()

        if total_count and assigned_count == total_count:
            new_state = OutboundWarehouseOrderState.COMPLETED
        elif assigned_count:
            new_state = OutboundWarehouseOrderState.STARTED
        else:
            new_state = OutboundWarehouseOrderState.PENDING

        if warehouse_order.state == new_state:
            return

        old_state = warehouse_order.state
        warehouse_order.state = new_state
        warehouse_order.save(update_fields=["state", "changed"])
        audit_service.add_entry(
            warehouse_order,
            user=context.user_id,
            action=AuditAction.TRANSITION,
            reason=AuditMessages.WAREHOUSE_ORDER_STATE_CHANGED.CS.format(
                old_state=old_state,
                new_state=new_state,
            ),
            changes={"state": {"old": old_state, "new": new_state}},
        )

        if (
            new_state == OutboundWarehouseOrderState.COMPLETED
            and warehouse_order.order is not None
        ):
            outbound_orders_service.sync_state_after_warehouse_completion(
                warehouse_order.order,
                context,
            )

        if (
            old_state == OutboundWarehouseOrderState.PENDING
            and warehouse_order.manufacturing_order
        ):
            manufacturing_orders_service.transition_order(
                warehouse_order.manufacturing_order.code, context=context, action="next"
            )

    @classmethod
    def cancel_outbound_warehouse_order(
        cls,
        warehouse_order: OutboundWarehouseOrder,
        context: RequestContext,
    ) -> None:
        """
        Cancel an outbound warehouse order, releasing all assigned warehouse items
        and writing inverse WarehouseMovement entries (fixes bug #2).
        """
        with transaction.atomic():
            # Get all assigned items (warehouse_item is not None)
            assigned_order_items = list(
                warehouse_order.order_items.select_related(
                    "warehouse_item",
                    "warehouse_item__stock_product",
                    "warehouse_item__location",
                    "warehouse_item__batch",
                )
                .filter(warehouse_item__isnull=False)
                .all()
            )

            for order_item in assigned_order_items:
                warehouse_item = order_item.warehouse_item
                if warehouse_item:
                    # Recover original location from the pick movement (location is None after picking)
                    pick_movement = (
                        WarehouseMovement.objects.filter(
                            item=warehouse_item,
                            outbound_order_code=warehouse_order,
                            location_to=None,
                        )
                        .select_related("location_from")
                        .order_by("-moved_at")
                        .first()
                    )
                    original_location = (
                        pick_movement.location_from if pick_movement else None
                    )

                    # Write inverse WarehouseMovement (location_to=original, location_from=None for cancellation)
                    WarehouseMovement.objects.create(
                        location_from=None,  # Cancellation - no source
                        location_to=original_location,  # Return to original location
                        outbound_order_code=warehouse_order,
                        stock_product=warehouse_item.stock_product,
                        amount=order_item.amount,
                        item=warehouse_item,
                        batch=warehouse_item.batch,
                        worker=User.objects.get(pk=context.user_id)
                        if context.user_id
                        else None,
                    )

                    # Restore item location
                    warehouse_item.location = original_location
                    warehouse_item.save(update_fields=["location_id", "changed"])

                    # Clear the assignment
                    order_item.warehouse_item = None
                    order_item.price_at_shipment = None
                    order_item.save(
                        update_fields=["warehouse_item", "price_at_shipment", "changed"]
                    )

                    audit_service.add_entry(
                        order_item,
                        action=AuditAction.UPDATE,
                        user=context.user_id,
                        reason=AuditMessages.WAREHOUSE_ORDER_CANCELLED.CS.format(
                            warehouse_order_code=warehouse_order.code
                        ),
                        changes={
                            "warehouse_item": {"old": warehouse_item.pk, "new": None},
                            "price_at_shipment": {
                                "old": str(order_item.price_at_shipment),
                                "new": None,
                            },
                        },
                    )

            # Transition warehouse order to CANCELLED
            old_state = warehouse_order.state
            warehouse_order.state = OutboundWarehouseOrderState.CANCELLED
            warehouse_order.save(update_fields=["state", "changed"])

            audit_service.add_entry(
                warehouse_order,
                action=AuditAction.TRANSITION,
                user=context.user_id,
                reason=AuditMessages.WAREHOUSE_ORDER_CANCELLED.CS.format(
                    warehouse_order_code=warehouse_order.code
                ),
                changes={
                    "state": {
                        "old": old_state,
                        "new": OutboundWarehouseOrderState.CANCELLED,
                    }
                },
            )

    @classmethod
    def assign_outbound_item(
        cls,
        warehouse_order_code: str,
        order_item_id: int,
        warehouse_item_id: int,
        context: RequestContext,
        amount: Decimal | None = None,
    ) -> OutboundWarehouseOrderSchema:
        warehouse_order = OutboundWarehouseOrder.objects.select_related("order").get(
            code=warehouse_order_code
        )
        if warehouse_order.state not in (
            OutboundWarehouseOrderState.PENDING,
            OutboundWarehouseOrderState.STARTED,
        ):
            raise WarehouseGenericError(
                f"Warehouse order '{warehouse_order_code}' is not editable."
            )

        order_item = OutboundWarehouseOrderItem.objects.select_related(
            "warehouse_order",
            "stock_product",
            "desired_package_type",
            "desired_batch",
        ).get(pk=order_item_id, warehouse_order=warehouse_order)
        if order_item.warehouse_item is not None:
            raise WarehouseGenericError(
                f"Warehouse order item '{order_item_id}' is already assigned."
            )

        candidate = (
            cls._get_outbound_item_candidates_qs(order_item)
            .select_related(
                "stock_product",
                "location",
                "batch",
                "package_type",
            )
            .filter(pk=warehouse_item_id)
            .first()
        )
        if candidate is None:
            # Check if warehouse item exists at all
            warehouse_item_exists = WarehouseItem.objects.filter(
                pk=warehouse_item_id
            ).first()
            if not warehouse_item_exists:
                raise WarehouseGenericError(
                    f"Warehouse item '{warehouse_item_id}' does not exist."
                )
            # Check if it's already assigned
            if (
                hasattr(warehouse_item_exists, "outbound_assignment")
                and warehouse_item_exists.outbound_assignment
            ):
                raise WarehouseGenericError(
                    f"Warehouse item '{warehouse_item_id}' is already assigned to order item '{warehouse_item_exists.outbound_assignment.pk}'."
                )
            # Check product match
            if warehouse_item_exists.stock_product != order_item.stock_product:
                raise WarehouseGenericError(
                    f"Warehouse item '{warehouse_item_id}' product '{warehouse_item_exists.stock_product.code}' does not match order requirement '{order_item.stock_product.code}'."
                )
            # Check package type match
            if (
                order_item.desired_package_type is not None
                and warehouse_item_exists.package_type
                != order_item.desired_package_type
            ):
                raise WarehouseGenericError(
                    f"Warehouse item '{warehouse_item_id}' package type '{warehouse_item_exists.package_type}' does not match order requirement '{order_item.desired_package_type}'."
                )
            # Check batch match
            if (
                order_item.desired_batch is not None
                and warehouse_item_exists.batch != order_item.desired_batch
            ):
                raise WarehouseGenericError(
                    f"Warehouse item '{warehouse_item_id}' batch '{warehouse_item_exists.batch}' does not match order requirement '{order_item.desired_batch}'."
                )
            # Generic fallback
            raise WarehouseGenericError(
                f"Warehouse item '{warehouse_item_id}' does not match outbound requirement."
            )

        requested_amount = (
            amount if amount is not None else Decimal(str(order_item.amount))
        )

        # CRITICAL VALIDATION: Ensure requested amount doesn't exceed available
        if requested_amount > candidate.amount:
            raise WarehouseGenericError(
                f"Cannot pick {requested_amount} units - only {candidate.amount} available in warehouse item '{warehouse_item_id}'."
            )

        # CRITICAL VALIDATION: Ensure requested amount is positive
        if requested_amount <= 0:
            raise WarehouseGenericError(
                f"Requested amount must be positive, got {requested_amount}."
            )

        with transaction.atomic():
            # Re-fetch candidate with lock and re-validate after acquiring lock
            candidate = WarehouseItem.objects.select_for_update().get(pk=candidate.pk)
            if requested_amount > candidate.amount:
                raise WarehouseGenericError(
                    f"Cannot pick {requested_amount} units - only {candidate.amount} available in warehouse item '{warehouse_item_id}' (changed since initial check)."
                )

            assigned_item, final_order_item = (
                cls._handle_outbound_item_assignment_with_splitting(
                    warehouse_item=candidate,
                    order_item=order_item,
                    requested_amount=requested_amount,
                    context=context,
                )
            )
            final_order_item.warehouse_item = assigned_item
            final_order_item.price_at_shipment = (
                Decimal(str(final_order_item.amount))
                * assigned_item.stock_product.purchase_price
            )
            final_order_item.save(
                update_fields=["warehouse_item", "price_at_shipment", "changed"]
            )

            WarehouseMovement.objects.create(
                location_from=assigned_item.location,
                location_to=None,
                outbound_order_code=warehouse_order,
                stock_product=assigned_item.stock_product,
                amount=final_order_item.amount,
                item=assigned_item,
                batch=assigned_item.batch,
                worker=User.objects.get(pk=context.user_id)
                if context.user_id
                else None,
            )
            assigned_item.location = None
            assigned_item.save(update_fields=["location_id", "changed"])
            audit_service.add_entry(
                final_order_item,
                action=AuditAction.UPDATE,
                user=context.user_id,
                reason=AuditMessages.ORDER_CODE_REFERENCE.CS.format(
                    order_code=warehouse_order.code
                ),
                changes={"warehouse_item": {"old": None, "new": assigned_item.pk}},
            )

        cls._sync_outbound_warehouse_order_state(warehouse_order, context)
        return cls.get_outbound_warehouse_order(warehouse_order_code)

    @classmethod
    def create_child_outbound_warehouse_order(
        cls,
        parent_code: str,
        context: RequestContext,
        initial_state: OutboundWarehouseOrderState = OutboundWarehouseOrderState.PENDING,
    ) -> OutboundWarehouseOrder:
        parent_order = OutboundWarehouseOrder.objects.select_related("order").get(
            code=parent_code
        )
        return create_warehouse_order(  # type: ignore[return-value]
            WarehouseOrderKind.CHILD_OUTBOUND,
            context,
            primary_order=parent_order,
            initial_state=initial_state,
        )

    @classmethod
    def offload_outbound_items_to_child_order(
        cls,
        parent_code: str,
        items: list[tuple[int, Decimal]],
        context: RequestContext,
    ) -> OutboundWarehouseOrderSchema:
        parent_order = OutboundWarehouseOrder.objects.select_related("order").get(
            code=parent_code
        )

        existing_child = parent_order.derived_orders.filter(
            state__in=(
                OutboundWarehouseOrderState.PENDING,
                OutboundWarehouseOrderState.STARTED,
            )
        ).first()
        child_order = existing_child or cls.create_child_outbound_warehouse_order(
            parent_code,
            context,
            initial_state=OutboundWarehouseOrderState.PENDING,
        )

        with transaction.atomic():
            for order_item_id, amount in items:
                amount = Decimal(str(amount))
                order_item = parent_order.order_items.select_related(
                    "stock_product",
                    "desired_package_type",
                    "desired_batch",
                ).get(pk=order_item_id)

                if amount > order_item.amount:
                    raise WarehouseGenericError(
                        f"Requested offload amount ({amount}) exceeds item amount ({order_item.amount}) for order_item id={order_item_id}."
                    )
                if (
                    order_item.warehouse_item is not None
                    and amount != order_item.amount
                ):
                    raise WarehouseGenericError(
                        f"Assigned outbound item '{order_item_id}' can only be offloaded as a whole item."
                    )

                if amount == order_item.amount:
                    order_item.warehouse_order = child_order
                    order_item.save(update_fields=["warehouse_order", "changed"])
                    offloaded = order_item
                else:
                    order_item.amount -= amount
                    order_item.save(update_fields=["amount", "changed"])
                    offloaded = OutboundWarehouseOrderItem.objects.create(
                        warehouse_order=child_order,
                        source_order_item=order_item.source_order_item,
                        stock_product=order_item.stock_product,
                        amount=amount,
                        desired_package_type=order_item.desired_package_type,
                        desired_batch=order_item.desired_batch,
                        warehouse_item=order_item.warehouse_item,
                        index=order_item.index,
                    )

                audit_service.add_entry(
                    offloaded,
                    action=AuditAction.UPDATE,
                    user=context.user_id,
                    reason=AuditMessages.ITEM_OFFLOADED_TO_CHILD_ORDER.CS.format(
                        amount=amount,
                        child_code=child_order.code,
                    ),
                    changes={
                        "warehouse_order": {
                            "old": parent_code,
                            "new": child_order.code,
                        },
                        "amount": str(amount),
                    },
                )

            audit_service.add_entry(
                parent_order,
                action=AuditAction.OTHER,
                user=context.user_id,
                reason=AuditMessages.ITEM_OFFLOADED_TO_CHILD_ORDER.CS.format(
                    amount=sum(a for _, a in items),
                    child_code=child_order.code,
                ),
                changes={"child_order": child_order.code},
            )

        cls._sync_outbound_warehouse_order_state(parent_order, context)
        cls._sync_outbound_warehouse_order_state(child_order, context)
        return cls.get_outbound_warehouse_order(parent_code)

    @staticmethod
    def create_inbound_order(
        params: WarehouseOrderCreateSchema, context: RequestContext
    ) -> InboundWarehouseOrderSchema:
        purchase_order = InboundOrder.objects.get(code=params.purchase_order_code)

        with transaction.atomic():
            warehouse_order = cast(
                InboundWarehouseOrder,
                create_warehouse_order(
                    WarehouseOrderKind.INBOUND,
                    context,
                    purchase_order=purchase_order,
                ),
            )
            inbound_orders_service.transition_order(
                purchase_order.code,
                context=context,
                target_state=InboundOrderState.RECEIVING,
            )

        warehouse_order.refresh_from_db()
        return warehouse_inbound_order_orm_to_schema(warehouse_order)

    @classmethod
    def confirm_arrival(
        cls, code: str, location_code: str, context: RequestContext
    ) -> None:
        with transaction.atomic():
            # Lock the warehouse order to prevent concurrent arrivals
            w_order = (
                InboundWarehouseOrder.objects.select_for_update()
                .select_related("order", "manufacturing_order")
                .get(code=code)
            )

            if w_order.state != InboundWarehouseOrderState.IN_TRANSIT:
                raise WarehouseGenericError(
                    f"Warehouse order '{code}' (state={w_order.state}) has to be in transit in order to confirm arrival."
                )

            # Idempotency guard: prevent duplicate order items on retry
            if w_order.order_items.exists():
                raise WarehouseGenericError(
                    f"Warehouse order '{code}' arrival has already been confirmed."
                )

            location = WarehouseLocation.objects.get(code=location_code)

            w_order.pickup_location = location
            w_order.save(update_fields=["pickup_location"])

            if w_order.order:
                source_items = [
                    (pi.stock_product, pi.amount, pi.unit_price)
                    for pi in w_order.order.items.order_by("index", "created")
                ]
            elif w_order.manufacturing_order:
                mfg_order = w_order.manufacturing_order
                source_items = []
                for mi in mfg_order.items.order_by("index", "created"):
                    total_frozen_cost = OutboundWarehouseOrderItem.objects.filter(
                        warehouse_order__manufacturing_order=mfg_order,
                        source_manufacturing_item=mi,
                    ).aggregate(total=Sum("price_at_shipment")).get("total") or Decimal(
                        "0"
                    )
                    unit_price = (
                        total_frozen_cost / mi.out_amount
                        if mi.out_amount > 0
                        else Decimal("0")
                    )
                    source_items.append((mi.out_product, mi.out_amount, unit_price))
            else:
                source_items = []

            for index, (stock_product, amount, unit_price) in enumerate(source_items):
                order_item = InboundWarehouseOrderItem.objects.create(
                    warehouse_order=w_order,
                    stock_product=stock_product,
                    amount=amount,
                    unit_price_at_receipt=unit_price,
                    tracking_level=TrackingLevel.FUNGIBLE,
                    index=index,
                )
                audit_service.add_entry(
                    order_item,
                    action=AuditAction.CREATE,
                    user=context.user_id,
                    reason=AuditMessages.ORDER_CODE_REFERENCE.CS.format(
                        order_code=w_order.code
                    ),
                )

            # Move state transition INSIDE atomic block to fix idempotency (bug #3)
            old_state = w_order.state
            w_order.state = InboundWarehouseOrderState.DRAFT
            w_order.save(update_fields=["state", "changed"])
            audit_service.add_entry(
                w_order,
                user=context.user_id,
                action=AuditAction.TRANSITION,
                reason=AuditMessages.WAREHOUSE_ORDER_STATE_CHANGED.CS.format(
                    old_state=old_state, new_state=InboundWarehouseOrderState.DRAFT
                ),
                changes={
                    "state": {"old": old_state, "new": InboundWarehouseOrderState.DRAFT}
                },
            )

    @staticmethod
    def get_warehouse_availability(stock_product_code: str) -> Decimal:
        return WarehouseItem.physical_stock.filter(
            stock_product__code=stock_product_code
        ).total_amount()
        # .aggregate(total_amount=Sum("amount"))
        # .get("total_amount")
        # or 0.0

    @staticmethod
    def get_incoming_availability(stock_product_code: str) -> Decimal:
        """Get total amount of incoming items (from inbound order items not yet completed)"""
        from apps.warehouse.models.orders import InboundOrderItem

        return InboundOrderItem.objects.filter(
            stock_product__code=stock_product_code,
            order__state__in=(
                InboundOrderState.DRAFT,
                InboundOrderState.SUBMITTED,
                InboundOrderState.RECEIVING,
            ),
        ).aggregate(total_amount=Sum("amount")).get("total_amount") or Decimal("0")

    @staticmethod
    def get_booked_availability(stock_product_code: str) -> Decimal:
        """Get total amount booked in outbound order items (from SUBMITTED until completed)"""
        from apps.warehouse.models.orders import OutboundOrderItem

        return OutboundOrderItem.objects.filter(
            stock_product__code=stock_product_code,
            order__state__in=(
                OutboundOrderState.SUBMITTED,
                OutboundOrderState.PICKING,
                OutboundOrderState.PACKING,
                OutboundOrderState.SHIPPING,
            ),
        ).aggregate(total_amount=Sum("amount")).get("total_amount") or Decimal("0")

    @classmethod
    def get_total_availability(
        cls, stock_product_code: str
    ) -> ProductWarehouseAvailability:
        warehouse_amount = cls.get_warehouse_availability(stock_product_code)
        incoming_amount = cls.get_incoming_availability(stock_product_code)
        booked_amount = cls.get_booked_availability(stock_product_code)

        return ProductWarehouseAvailability(
            total_amount=warehouse_amount,
            available_amount=warehouse_amount - booked_amount,
            incoming_amount=incoming_amount,
        )

    @staticmethod
    def preview_packaging(
        order_item_id: int, product_code: str, package_name: str, amount: float
    ) -> list[WarehouseItemSchema]:
        order_item = InboundWarehouseOrderItem.objects.select_related(
            "warehouse_order__pickup_location",
            "warehouse_order__pickup_location__warehouse",
        ).get(pk=order_item_id)
        location = order_item.warehouse_order.pickup_location
        if not location:
            raise WarehouseGenericError(
                "Warehouse order has no pickup location set — cannot preview packaging."
            )
        product = StockProduct.objects.get(code=product_code)
        package = PackageType.objects.get(name=package_name)

        if not package.unit_of_measure:
            package_amount_in_product_uom: float | None = float(order_item.amount)
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
                    location=location_orm_to_schema(location),
                    created=timezone.now(),
                    changed=timezone.now(),
                )
            )

        return items

    @staticmethod
    def preview_batching(
        order_item_id: int,
        product_code: str,
        amount: float,
        batch_code: str | None = None,
    ) -> list[WarehouseItemSchema]:
        order_item = InboundWarehouseOrderItem.objects.select_related(
            "warehouse_order__pickup_location",
            "warehouse_order__pickup_location__warehouse",
        ).get(pk=order_item_id)
        location = order_item.warehouse_order.pickup_location
        if not location:
            raise WarehouseGenericError(
                "Warehouse order has no pickup location set — cannot preview batching."
            )
        product = StockProduct.objects.get(code=product_code)

        if batch_code:
            barcode = Barcode.objects.select_related("content_type").get(
                code=batch_code
            )
            if barcode.content_type.model_class() is not Batch:
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
                        id=-1,
                        code=batch_code or "autogen-batch-01234",
                        barcode_type=BarcodeType.EAN13,
                        is_primary=True,
                        changed=timezone.now(),
                        created=timezone.now(),
                    ),
                    changed=timezone.now(),
                    created=timezone.now(),
                ),
                location=location_orm_to_schema(location),
                created=timezone.now(),
                changed=timezone.now(),
            )
        ]

        return items

    @staticmethod
    def preview_serial_tracking(
        order_item_id: int,
        product_code: str,
        amount: float,
    ) -> list[WarehouseItemSchema]:
        order_item = InboundWarehouseOrderItem.objects.select_related(
            "warehouse_order__pickup_location",
            "warehouse_order__pickup_location__warehouse",
        ).get(pk=order_item_id)
        location = order_item.warehouse_order.pickup_location
        if not location:
            raise WarehouseGenericError(
                "Warehouse order has no pickup location set — cannot preview serial tracking."
            )
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
                location=location_orm_to_schema(location),
                created=timezone.now(),
                changed=timezone.now(),
            )
            for _ in range(num_of_items)
        ]

        return items

    @staticmethod
    def add_or_remove_inbound_order_items(
        order_code: str,
        to_be_removed: list[int],
        to_be_added: list[DraftItemAddSchema],
        context: RequestContext,
    ) -> InboundWarehouseOrderSchema:
        order = InboundWarehouseOrder.objects.get(code=order_code)

        raise_if_readonly(order)

        try:
            with transaction.atomic():
                for item_id in to_be_removed:
                    order.order_items.get(pk=item_id).delete()
                next_index = (
                    order.order_items.order_by("-index")
                    .values_list("index", flat=True)
                    .first()
                    or -1
                ) + 1
                for i, item in enumerate(to_be_added):
                    new_order_item = InboundWarehouseOrderItem.objects.create(
                        warehouse_order=order,
                        stock_product=StockProduct.objects.get(code=item.product_code),
                        amount=Decimal(str(item.amount)),
                        index=next_index + i,
                    )
                    audit_service.add_entry(
                        new_order_item,
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
        order_item_id: int,
        to_be_added: list[WarehouseItemSchema],
        context: RequestContext,
    ) -> InboundWarehouseOrderSchema:
        """
        Configure tracking for a draft order line.

        The fungible InboundWarehouseOrderItem identified by order_item_id is
        split into one or more tracked InboundWarehouseOrderItem rows based on
        the supplied breakdown.  Total amounts (UoM) are validated to match.
        WarehouseItems do not exist yet — they are materialised at confirmation.
        """
        order = InboundWarehouseOrder.objects.get(code=order_code)
        raise_if_readonly(order)

        source_item = InboundWarehouseOrderItem.objects.get(
            pk=order_item_id,
            warehouse_order=order,
            tracking_level=TrackingLevel.FUNGIBLE,
        )

        remaining_amount = source_item.amount - Decimal(
            sum(item.amount for item in to_be_added)
        )
        try:
            with transaction.atomic():
                for new_item in to_be_added:
                    batch_barcode: str | None = None
                    if new_item.batch and new_item.batch.primary_barcode:
                        batch_barcode = new_item.batch.primary_barcode.code

                    package_type = (
                        PackageType.objects.get(name=new_item.package.type)
                        if new_item.package
                        else None
                    )
                    InboundWarehouseOrderItem.objects.create(
                        warehouse_order=order,
                        stock_product=StockProduct.objects.get(
                            code=new_item.product.code
                        ),
                        amount=Decimal(str(new_item.amount)),
                        tracking_level=new_item.tracking_level,
                        package_type=package_type,
                        unit_price_at_receipt=source_item.unit_price_at_receipt,
                        index=source_item.index,
                        batch_barcode=batch_barcode,
                    )
                    audit_service.add_entry(
                        order,
                        action=AuditAction.UPDATE,
                        user=context.user_id,
                        reason=AuditMessages.TRACKING_SETUP.CS.format(
                            order_code=order_code,
                            tracking_level=new_item.tracking_level,
                        ),
                    )
                if remaining_amount > 0:
                    source_item.amount = remaining_amount
                    source_item.save(update_fields=["amount"])
                else:
                    source_item.delete()
        except ObjectDoesNotExist as exc:
            raise WarehouseItemBadRequestError(str(exc))

        return warehouse_inbound_order_orm_to_schema(
            InboundWarehouseOrder.objects.get(code=order_code)
        )

    @staticmethod
    def dissolve_inbound_order_item(
        order_code: str,
        order_item_id: int,
    ) -> InboundWarehouseOrderSchema:
        order = InboundWarehouseOrder.objects.get(code=order_code)

        raise_if_readonly(order)

        item = InboundWarehouseOrderItem.objects.get(
            pk=order_item_id, warehouse_order=order
        )

        existing_fungible = (
            order.order_items.filter(
                stock_product=item.stock_product,
                package_type__isnull=True,
                tracking_level=TrackingLevel.FUNGIBLE,
            )
            .exclude(pk=item.pk)
            .first()
        )

        try:
            with transaction.atomic():
                if not existing_fungible:
                    InboundWarehouseOrderItem.objects.create(
                        warehouse_order=order,
                        stock_product=item.stock_product,
                        amount=item.amount,
                        tracking_level=TrackingLevel.FUNGIBLE,
                        unit_price_at_receipt=item.unit_price_at_receipt,
                        index=item.index,
                    )
                else:
                    existing_fungible.amount += item.amount
                    existing_fungible.save(update_fields=["amount"])

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
        order_item_id: int,
        amount: float | Decimal,
        context: RequestContext,
    ) -> InboundWarehouseOrderSchema:
        amount = Decimal(amount)
        warehouse_order = InboundWarehouseOrder.objects.get(code=warehouse_order_code)

        if warehouse_order.state != InboundWarehouseOrderState.DRAFT:
            raise WarehouseGenericError(
                f"Warehouse order '{warehouse_order.code}' is already confirmed and read-only."
            )

        order_item = InboundWarehouseOrderItem.objects.select_related(
            "stock_product", "warehouse_order__order"
        ).get(pk=order_item_id, warehouse_order=warehouse_order)

        stock_product = order_item.stock_product
        order = warehouse_order.order
        if not order:
            raise WarehouseGenericError(
                f"Warehouse order '{warehouse_order.code}' has no inbound order attached,"
                "manufacturing warehouse orders cannot be moved to a credit note."
            )

        with transaction.atomic():
            if amount > order_item.amount:
                raise WarehouseGenericError(
                    f"Requested amount ({amount}) exceeds item amount: {order_item.amount} ({stock_product.name})"
                )

            note, created = inbound_orders_service.get_or_create_credit_note(
                order.code, context
            )
            note_model = CreditNoteToSupplier.objects.get(order=order)
            if note_model.state != CreditNoteState.DRAFT:
                raise WarehouseGenericError(
                    f"Credit Note '{note_model.code}' is already confirmed and read-only"
                )

            existing_item = CreditNoteToSupplierItem.objects.filter(
                credit_note__code=note.code, stock_product=stock_product
            ).first()
            if existing_item:
                existing_item.amount += amount
                existing_item.save()
            else:
                CreditNoteToSupplierItem.objects.create(
                    stock_product=stock_product,
                    amount=amount,
                    credit_note=note_model,
                    unit_price=order_item.unit_price_at_receipt,
                )

            if amount == order_item.amount:
                order_item.delete()
            else:
                order_item.amount -= amount
                order_item.save(update_fields=["amount"])

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
    def _recalculate_purchase_prices_for_confirmed_order(
        cls,
        order_items: list[InboundWarehouseOrderItem],
        context: RequestContext,
    ) -> None:
        adjustments_by_product: dict[str, dict[str, Decimal]] = {}

        for order_item in order_items:
            product_code = order_item.stock_product.code
            adjustment = adjustments_by_product.setdefault(
                product_code,
                {"amount": Decimal("0"), "total_cost": Decimal("0")},
            )
            adjustment["amount"] += order_item.amount
            adjustment["total_cost"] += (
                order_item.amount * order_item.unit_price_at_receipt
            )

        for product_code, adjustment in adjustments_by_product.items():
            if adjustment["amount"] <= 0:
                continue

            cls.recalculate_average_purchase_price(
                product_code=product_code,
                amount=adjustment["amount"],
                unit_price=adjustment["total_cost"] / adjustment["amount"],
                context=context,
            )

    @classmethod
    def confirm_draft(cls, code: str, context: RequestContext) -> None:
        with transaction.atomic():
            # Lock the warehouse order to prevent concurrent confirmations
            w_order = InboundWarehouseOrder.objects.select_for_update().get(code=code)

            if w_order.state != InboundWarehouseOrderState.DRAFT:
                raise WarehouseGenericError(
                    f"Warehouse order '{code}' (state={w_order.state}) has to be in draft state in order to be confirmed."
                )

            # Idempotency guard: prevent duplicate materialisation on retry
            if w_order.items.exists():
                raise WarehouseGenericError(
                    f"Warehouse order '{code}' has already been confirmed and items materialized."
                )

            location = w_order.pickup_location
            if not location:
                raise WarehouseGenericError(
                    f"Warehouse order '{code}' has no pickup location set — cannot materialise items."
                )

            order_items = list(
                w_order.order_items.select_related(
                    "stock_product", "package_type"
                ).all()
            )
            cls._recalculate_purchase_prices_for_confirmed_order(
                order_items,
                context=context,
            )

            for order_item in order_items:
                batch = None
                if order_item.batch_barcode:
                    batch, _ = get_or_create_batch(order_item.batch_barcode)

                item = WarehouseItem.objects.create(
                    stock_product=order_item.stock_product,
                    tracking_level=order_item.tracking_level,
                    amount=order_item.amount,
                    order_in=w_order,
                    source_order_item=order_item,
                    location=location,
                    package_type=order_item.package_type,
                    batch=batch,
                )
                if order_item.tracking_level in (
                    TrackingLevel.SERIALIZED_PIECE,
                    TrackingLevel.SERIALIZED_PACKAGE,
                ):
                    item.attach_barcode(
                        code=generate_warehouse_item_code(), is_primary=True
                    )
                audit_service.add_entry(
                    item,
                    action=AuditAction.CREATE,
                    user=context.user_id,
                    reason=AuditMessages.ORDER_CODE_REFERENCE.CS.format(
                        order_code=w_order.code
                    ),
                )

                # Write WarehouseMovement for initial materialisation (bug #9)
                WarehouseMovement.objects.create(
                    location_from=None,  # Initial receipt - no source location
                    location_to=location,
                    inbound_order_code=w_order,
                    stock_product=item.stock_product,
                    amount=item.amount,
                    item=item,
                    batch=batch,
                    worker=User.objects.get(pk=context.user_id)
                    if context.user_id
                    else None,
                )

            # Move state transition INSIDE atomic block to fix idempotency (bug #3)
            old_state = w_order.state
            w_order.state = InboundWarehouseOrderState.PENDING
            w_order.save(update_fields=["state", "changed"])
            audit_service.add_entry(
                w_order,
                user=context.user_id,
                action=AuditAction.TRANSITION,
                reason=AuditMessages.WAREHOUSE_ORDER_STATE_CHANGED.CS.format(
                    old_state=old_state, new_state=InboundWarehouseOrderState.PENDING
                ),
                changes={
                    "state": {
                        "old": old_state,
                        "new": InboundWarehouseOrderState.PENDING,
                    }
                },
            )

        # These service calls stay outside the atomic block as they're separate operations
        # Manufacturing-linked inbound orders have no InboundOrder to transition.
        if w_order.manufacturing_order_id:
            return
        inbound_order = InboundOrder.objects.get(warehouse_orders__code=code)
        inbound_orders_service.transition_order(
            inbound_order.code,
            context=context,
            target_state=InboundOrderState.PUTAWAY,
        )
        if credit_note := getattr(inbound_order, "credit_note", None):
            inbound_orders_service.transition_credit_note(
                credit_note.code,
                CreditNoteState.CONFIRMED,
                context=context,
            )

    @classmethod
    def transition_inbound_order(
        cls,
        code: str,
        context: RequestContext,
        location_code: str | None = None,
    ) -> None:
        current_state = cls.get_inbound_warehouse_order_model(code).state

        if current_state == InboundWarehouseOrderState.IN_TRANSIT:
            if not location_code:
                raise WarehouseGenericError(
                    "location_code is required when confirming arrival from in transit"
                )
            cls.confirm_arrival(code=code, location_code=location_code, context=context)
            return

        if current_state == InboundWarehouseOrderState.DRAFT:
            cls.confirm_draft(code, context=context)
            return

        raise WarehouseGenericError(
            f"Unsupported transition from state '{current_state}'"
        )

    @classmethod
    def set_order_state(
        cls,
        code: str,
        target_state: InboundWarehouseOrderState,
        context: RequestContext,
        location_code: str | None = None,
    ) -> None:
        # Backward-compatible wrapper for legacy callers.
        current_state = cls.get_inbound_warehouse_order_model(code).state
        if target_state == current_state:
            return

        current_state = cls.get_inbound_warehouse_order_model(code).state

        if target_state == InboundWarehouseOrderState.DRAFT:
            if current_state == InboundWarehouseOrderState.IN_TRANSIT:
                if not location_code:
                    raise WarehouseGenericError(
                        "location_code is required when confirming arrival from in transit"
                    )
                cls.confirm_arrival(
                    code=code, location_code=location_code, context=context
                )
                return

            raise WarehouseGenericError(
                f"Unsupported state transition '{current_state}' -> '{target_state}'"
            )

        if target_state == InboundWarehouseOrderState.PENDING:
            cls.confirm_draft(code, context=context)
            return

        raise WarehouseGenericError(f"Unsupported state transition '{target_state}'")

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
        if warehouse_order.state in (
            InboundWarehouseOrderState.DRAFT,
            InboundWarehouseOrderState.IN_TRANSIT,
        ):
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
            movement_service.move_item(item, context, new_location)

            if warehouse_order.items.filter(location__is_putaway=True).count() == 0:
                cls.transition_order(
                    warehouse_order_code,
                    InboundWarehouseOrderState.COMPLETED,
                    context=context,
                )
                if warehouse_order.order:
                    if (
                        warehouse_order.order.warehouse_orders.exclude(
                            state=InboundWarehouseOrderState.COMPLETED
                        ).count()
                        == 0
                    ):
                        inbound_orders_service.transition_order(
                            warehouse_order.order.code,
                            context=context,
                            target_state=InboundOrderState.COMPLETED,
                        )
            else:
                cls.transition_order(
                    warehouse_order_code,
                    InboundWarehouseOrderState.STARTED,
                    context=context,
                )

    @classmethod
    def move_item_standalone(
        cls,
        request: MoveItemRequest,
        context: RequestContext,
    ) -> None:
        """Move a warehouse item to a new location, optionally unpacking a partial amount."""
        try:
            item = WarehouseItem.physical_stock.select_related(
                "stock_product",
                "location",
                "batch",
                "package_type",
                "order_in",
                "source_order_item",
            ).get(pk=request.item_id)
        except WarehouseItem.DoesNotExist as exc:
            raise WarehouseItemNotFoundError(
                f"Warehouse item '{request.item_id}' not found"
            ) from exc

        if str(item.location.code) == request.location_to_code:
            raise WarehouseItemBadRequestError(
                f"Item is already at location '{request.location_to_code}'"
            )

        amount = request.amount

        if amount is not None and amount <= 0:
            raise WarehouseItemBadRequestError("Amount must be positive")

        if amount is not None and item.amount < amount:
            raise WarehouseItemBadRequestError(
                f"Requested amount ({amount}) exceeds available amount ({item.amount})"
            )

        with transaction.atomic():
            if request.unpack:
                if item.tracking_level != TrackingLevel.SERIALIZED_PACKAGE:
                    raise WarehouseItemBadRequestError(
                        "Unpack is only supported for SERIALIZED_PACKAGE items"
                    )
                if amount is None:
                    raise WarehouseItemBadRequestError(
                        "Amount is required for unpack operations"
                    )
                unpacked = cls._unpack_package(item, amount, context)
                movement_service.move_item(unpacked, context, request.location_to_code)
            else:
                movement_service.move_item(
                    item, context, request.location_to_code, amount
                )

    @classmethod
    def create_child_warehouse_order(
        cls,
        parent_code: str,
        context: RequestContext,
        initial_state: InboundWarehouseOrderState = InboundWarehouseOrderState.DRAFT,
    ) -> InboundWarehouseOrder:
        parent_order = InboundWarehouseOrder.objects.select_related(
            "order", "pickup_location"
        ).get(code=parent_code)
        return create_warehouse_order(  # type: ignore[return-value]
            WarehouseOrderKind.CHILD_INBOUND,
            context,
            primary_order=parent_order,
            initial_state=initial_state,
        )

    @classmethod
    def offload_items_to_child_order(
        cls,
        parent_code: str,
        items: list[tuple[int, Decimal]],
        context: RequestContext,
    ) -> InboundWarehouseOrderSchema:
        """
        Move a list of (item_id, amount) pairs from the parent inbound
        warehouse order into a child order.

        DRAFT state → item_ids reference InboundWarehouseOrderItem (draft snapshot).
        PENDING/STARTED state → item_ids reference WarehouseItem (materialised).
        A new child order is created automatically if none exists yet.
        """
        parent_order = InboundWarehouseOrder.objects.select_related("order").get(
            code=parent_code
        )

        existing_child = parent_order.derived_orders.filter(
            state=InboundWarehouseOrderState.DRAFT
            if parent_order.state == InboundWarehouseOrderState.DRAFT
            else InboundWarehouseOrderState.PENDING
        ).first()
        if existing_child:
            child_order = existing_child
        elif parent_order.state == InboundWarehouseOrderState.DRAFT:
            child_order = cls.create_child_warehouse_order(parent_code, context)
        else:
            child_order = cls.create_child_warehouse_order(
                parent_code,
                context,
                initial_state=InboundWarehouseOrderState.PENDING,
            )

        with transaction.atomic():
            if parent_order.state == InboundWarehouseOrderState.DRAFT:
                # ── Draft mode: move InboundWarehouseOrderItem rows ──────────
                for order_item_id, amount in items:
                    amount = Decimal(str(amount))
                    order_item = parent_order.order_items.select_related(
                        "stock_product", "package_type"
                    ).get(pk=order_item_id)

                    if amount > order_item.amount:
                        raise WarehouseGenericError(
                            f"Requested offload amount ({amount}) exceeds item amount "
                            f"({order_item.amount}) for order_item id={order_item_id}."
                        )

                    if amount == order_item.amount:
                        order_item.warehouse_order = child_order
                        order_item.save(update_fields=["warehouse_order"])
                        offloaded = order_item
                    else:
                        order_item.amount -= amount
                        order_item.save(update_fields=["amount"])
                        offloaded = InboundWarehouseOrderItem.objects.create(
                            warehouse_order=child_order,
                            stock_product=order_item.stock_product,
                            tracking_level=order_item.tracking_level,
                            amount=amount,
                            package_type=order_item.package_type,
                            unit_price_at_receipt=order_item.unit_price_at_receipt,
                            index=order_item.index,
                            batch_barcode=order_item.batch_barcode,
                        )

                    audit_service.add_entry(
                        offloaded,
                        action=AuditAction.UPDATE,
                        user=context.user_id,
                        reason=AuditMessages.ITEM_OFFLOADED_TO_CHILD_ORDER.CS.format(
                            amount=amount, child_code=child_order.code
                        ),
                        changes={
                            "warehouse_order": {
                                "old": parent_code,
                                "new": child_order.code,
                            },
                            "amount": str(amount),
                        },
                    )

            else:
                # ── Post-confirmation mode: move WarehouseItem rows ───────────
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
                        offloaded_wh = item
                    else:
                        item.amount -= amount
                        item.save()
                        offloaded_wh = WarehouseItem.objects.create(
                            stock_product=item.stock_product,
                            tracking_level=item.tracking_level,
                            amount=amount,
                            location=item.location,
                            order_in=child_order,
                            source_order_item=item.source_order_item,
                            batch=item.batch,
                            package_type=item.package_type,
                        )

                    audit_service.add_entry(
                        offloaded_wh,
                        action=AuditAction.UPDATE,
                        user=context.user_id,
                        reason=AuditMessages.ITEM_OFFLOADED_TO_CHILD_ORDER.CS.format(
                            amount=amount, child_code=child_order.code
                        ),
                        changes={
                            "order_in": {"old": parent_code, "new": child_order.code},
                            "amount": str(amount),
                        },
                    )

                    # Write WarehouseMovement for reparent operation (fix bug #9)
                    WarehouseMovement.objects.create(
                        location_from=offloaded_wh.location,
                        location_to=offloaded_wh.location,  # Same location, reparent operation
                        inbound_order_code=child_order,
                        stock_product=offloaded_wh.stock_product,
                        amount=amount,
                        item=offloaded_wh,
                        batch=offloaded_wh.batch,
                        worker=User.objects.get(pk=context.user_id)
                        if context.user_id
                        else None,
                    )

            audit_service.add_entry(
                parent_order,
                action=AuditAction.OTHER,
                user=context.user_id,
                reason=AuditMessages.ITEM_OFFLOADED_TO_CHILD_ORDER.CS.format(
                    amount=sum(a for _, a in items), child_code=child_order.code
                ),
                changes={"child_order": child_order.code},
            )

        return cls.get_inbound_warehouse_order(parent_code)


warehouse_service = WarehouseService()
