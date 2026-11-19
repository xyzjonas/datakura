"""
Goods taken back from a customer ("vratka").

For an order that has already been sent out any amount of any (physical) sold
row can be received back. One return (one `create_return` call) produces:

- returned rows on the sales order (`OutboundOrderItem.is_returned`) - never
  picked, subtracted from the order totals / margin,
- a receipt (příjemka) linked to the sales order (`InboundWarehouseOrder.return_order`),
  that goes through the usual receiving flow (arrival, put-away),
- a credit note (dobropis) to the customer with the returned rows, confirmed
  together with the receipt and meant to be invoiced later.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import cast

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.exceptions import (
    WarehouseGenericError,
    WarehouseItemBadRequestError,
)
from apps.warehouse.core.query_optimization import inbound_warehouse_orders_for_schema
from apps.warehouse.core.schemas.warehouse import (
    InboundWarehouseOrderSchema,
    ReturnedItemMatchSchema,
)
from apps.warehouse.core.services.warehouse_order_factory import (
    WarehouseOrderKind,
    create_warehouse_order,
)
from apps.warehouse.core.transformation import (
    batch_primary_barcode,
    warehouse_inbound_order_orm_to_schema,
    warehouse_item_orm_to_schema,
)
from apps.warehouse.models.barcode import Barcode
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.orders import (
    OutboundOrderReturnSchema,
    OutboundOrderSchema,
)
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.code_sequence import generate_next_sequential_code
from apps.warehouse.core.services.outbound_common import (
    outbound_order_schema_with_pricing,
)
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.orders import (
    CreditNoteState,
    CreditNoteToCustomer,
    CreditNoteToCustomerItem,
    OutboundOrder,
    OutboundOrderItem,
    OutboundOrderState,
)
from apps.warehouse.models.warehouse import (
    InboundWarehouseOrder,
    InboundWarehouseOrderItem,
    InboundWarehouseOrderState,
    TrackingLevel,
    WarehouseItem,
    WarehouseLocation,
    WarehouseMovement,
    OutboundWarehouseOrderItem,
)

CREDIT_NOTE_TO_CUSTOMER_PREFIX = "DO"
_MONEY = Decimal("0.0001")


class OrderReturnsService:
    # states of an order whose goods have left the warehouse
    RETURNABLE_STATES = (
        OutboundOrderState.SENT,
        OutboundOrderState.COMPLETED,
        OutboundOrderState.INVOICED,
        OutboundOrderState.WAITING_FOR_PAYMENT,
        OutboundOrderState.COMPLETED_PAID,
    )

    @staticmethod
    def returned_amount(item: OutboundOrderItem) -> Decimal:
        """Amount of a sold row that was already taken back."""
        return item.returned_items.aggregate(total=Sum("amount"))["total"] or Decimal(0)

    @classmethod
    def returnable_amount(cls, item: OutboundOrderItem) -> Decimal:
        return item.amount - cls.returned_amount(item)

    @staticmethod
    def unit_cost(item: OutboundOrderItem) -> Decimal:
        """
        Value the goods of a sold row come back with: the frozen cost they were
        shipped for, falling back to the current average purchase price.
        """
        shipped = OutboundWarehouseOrderItem.objects.filter(
            source_order_item=item, price_at_shipment__isnull=False
        ).aggregate(cost=Sum("price_at_shipment"), amount=Sum("amount"))
        if shipped["amount"]:
            return (shipped["cost"] / shipped["amount"]).quantize(
                _MONEY, rounding=ROUND_HALF_UP
            )
        return Decimal(str(item.stock_product.purchase_price or 0))

    @classmethod
    def create_return(
        cls,
        order_code: str,
        params: OutboundOrderReturnSchema,
        context: RequestContext,
    ) -> OutboundOrderSchema:
        with transaction.atomic():
            # serialize concurrent returns (amount caps) and index allocation
            order = OutboundOrder.objects.select_for_update().get(code=order_code)
            if order.state not in cls.RETURNABLE_STATES:
                raise WarehouseItemBadRequestError(
                    f"Goods of order '{order.code}' were not sent out yet, nothing to return."
                )

            requested: dict[int, Decimal] = {}
            for line in params.items:
                if line.item_index in requested:
                    raise WarehouseItemBadRequestError(
                        f"Item row {line.item_index + 1} is listed more than once."
                    )
                requested[line.item_index] = Decimal(str(line.amount))

            sources = {
                item.index: item
                for item in order.items.select_related("stock_product__type").filter(
                    is_returned=False, index__in=requested
                )
            }
            for index, amount in requested.items():
                source = sources.get(index)
                if source is None:
                    raise WarehouseItemBadRequestError(
                        f"Item row {index + 1} of order '{order.code}' does not exist."
                    )
                if source.stock_product.type.non_physical:
                    raise WarehouseItemBadRequestError(
                        f"'{source.stock_product.name}' is not a physical product, it cannot be returned."
                    )
                returnable = cls.returnable_amount(source)
                if amount > returnable:
                    raise WarehouseItemBadRequestError(
                        f"Cannot return {amount} of '{source.stock_product.name}', "
                        f"only {returnable} left to be returned."
                    )

            receipt = cast(
                InboundWarehouseOrder,
                create_warehouse_order(
                    WarehouseOrderKind.RETURN_INBOUND, context, sales_order=order
                ),
            )
            credit_note = CreditNoteToCustomer.objects.create(
                code=generate_next_sequential_code(
                    queryset=CreditNoteToCustomer.objects.all(),
                    prefix=CREDIT_NOTE_TO_CUSTOMER_PREFIX,
                ),
                order=order,
                warehouse_order=receipt,
                reason="Vratka zboží",
                state=CreditNoteState.DRAFT,
            )

            last = (
                order.items.order_by("-index").values_list("index", flat=True).first()
            )
            next_index = 0 if last is None else last + 1

            for index, amount in requested.items():
                source = sources[index]
                total_price = (source.total_price * amount / source.amount).quantize(
                    _MONEY, rounding=ROUND_HALF_UP
                )
                # returned goods are credited at the very (frozen) document price
                document_total_price = (
                    None
                    if source.document_total_price is None
                    else (
                        source.document_total_price * amount / source.amount
                    ).quantize(_MONEY, rounding=ROUND_HALF_UP)
                )
                OutboundOrderItem.objects.create(
                    order=order,
                    stock_product=source.stock_product,
                    amount=amount,
                    unit_price=source.unit_price,
                    total_price=total_price,
                    document_unit_price=source.document_unit_price,
                    document_total_price=document_total_price,
                    index=next_index,
                    required_origin_country=source.required_origin_country,
                    is_returned=True,
                    returned_from=source,
                    return_receipt=receipt,
                )
                next_index += 1
                CreditNoteToCustomerItem.objects.create(
                    credit_note=credit_note,
                    stock_product=source.stock_product,
                    amount=amount,
                    unit_price=source.unit_price,
                )

            audit_service.add_entry(
                credit_note,
                action=AuditAction.CREATE,
                user=context.user_id,
                reason=AuditMessages.CREDIT_NOTE_CREATED_FOR_OUTBOUND_ORDER.CS.format(
                    credit_note_code=credit_note.code
                ),
            )
            audit_service.add_entry(
                order,
                action=AuditAction.OTHER,
                user=context.user_id,
                reason=AuditMessages.GOODS_RETURNED_BY_CUSTOMER.CS.format(
                    receipt_code=receipt.code, credit_note_code=credit_note.code
                ),
                changes={
                    "returned": {
                        str(index + 1): str(amount)
                        for index, amount in requested.items()
                    },
                    "receipt": receipt.code,
                    "credit_note": credit_note.code,
                },
            )

        return outbound_order_schema_with_pricing(order)

    # ── receiving the very items we shipped ────────────────────────────────

    @staticmethod
    def _editable_return_receipt(code: str) -> InboundWarehouseOrder:
        receipt = InboundWarehouseOrder.objects.select_related("return_order").get(
            code=code
        )
        if receipt.return_order is None:
            raise WarehouseItemBadRequestError(
                f"Receipt '{code}' does not belong to a return of goods."
            )
        if receipt.state != InboundWarehouseOrderState.DRAFT:
            raise WarehouseItemBadRequestError(
                f"Receipt '{code}' can no longer be edited (state={receipt.state})."
            )
        return receipt

    @staticmethod
    def _shipped_item_or_raise(
        receipt: InboundWarehouseOrder, warehouse_item: WarehouseItem
    ) -> OutboundWarehouseOrderItem:
        """The pick `warehouse_item` left with - it has to be one of this return's order."""
        assignment = warehouse_item.live_outbound_assignment
        if assignment is None:
            raise WarehouseItemBadRequestError(
                f"Item {warehouse_item.pk} is not out of the warehouse, nothing to receive back."
            )
        if assignment.warehouse_order.order_id != receipt.return_order_id:
            raise WarehouseItemBadRequestError(
                f"Item {warehouse_item.pk} was not shipped with order "
                f"'{receipt.return_order.code}'."  # type: ignore[union-attr]
            )
        if InboundWarehouseOrderItem.objects.filter(
            returned_warehouse_item=warehouse_item,
            warehouse_order__state=InboundWarehouseOrderState.DRAFT,
        ).exists():
            raise WarehouseItemBadRequestError(
                f"Item {warehouse_item.pk} is already being received back."
            )
        return assignment

    @staticmethod
    def _open_line_for(
        receipt: InboundWarehouseOrder, warehouse_item: WarehouseItem
    ) -> InboundWarehouseOrderItem:
        line = (
            receipt.order_items.filter(
                stock_product=warehouse_item.stock_product,
                tracking_level=TrackingLevel.FUNGIBLE,
                returned_warehouse_item__isnull=True,
                amount__gte=warehouse_item.amount,
            )
            .order_by("index", "created")
            .first()
        )
        if line is None:
            raise WarehouseItemBadRequestError(
                f"'{warehouse_item.stock_product.name}' ({warehouse_item.amount}) "
                f"is not among the goods left to be received on '{receipt.code}'."
            )
        return line

    @classmethod
    def match_returned_item(cls, code: str, barcode: str) -> ReturnedItemMatchSchema:
        """Recognise a shipped item by the barcode it still carries."""
        receipt = cls._editable_return_receipt(code)
        found = (
            Barcode.objects.select_related("content_type").filter(code=barcode).first()
        )
        entity = found.content_object if found else None
        if not isinstance(entity, WarehouseItem):
            raise WarehouseItemBadRequestError(
                f"Barcode '{barcode}' does not identify a single warehouse item."
            )
        cls._shipped_item_or_raise(receipt, entity)
        line = cls._open_line_for(receipt, entity)
        return ReturnedItemMatchSchema(
            warehouse_item=warehouse_item_orm_to_schema(entity),
            order_item_id=line.pk,
            created=entity.created,
            changed=entity.changed,
        )

    @classmethod
    def claim_returned_item(
        cls,
        code: str,
        order_item_id: int,
        warehouse_item_id: int,
        context: RequestContext,
    ) -> InboundWarehouseOrderSchema:
        """
        Receive the very item we shipped back: the (fungible) line is split, one
        row now points at the existing item and no new item is created for it.
        """
        with transaction.atomic():
            receipt = cls._editable_return_receipt(code)
            warehouse_item = WarehouseItem.objects.select_for_update().get(
                pk=warehouse_item_id
            )
            cls._shipped_item_or_raise(receipt, warehouse_item)
            source = receipt.order_items.get(
                pk=order_item_id,
                stock_product=warehouse_item.stock_product,
                tracking_level=TrackingLevel.FUNGIBLE,
                returned_warehouse_item__isnull=True,
            )
            if source.amount < warehouse_item.amount:
                raise WarehouseItemBadRequestError(
                    f"Item {warehouse_item.pk} ({warehouse_item.amount}) is more than "
                    f"what is left to be received ({source.amount})."
                )

            InboundWarehouseOrderItem.objects.create(
                warehouse_order=receipt,
                stock_product=warehouse_item.stock_product,
                amount=warehouse_item.amount,
                tracking_level=warehouse_item.tracking_level,
                package_type=warehouse_item.package_type,
                unit_price_at_receipt=source.unit_price_at_receipt,
                source_order_item=source.source_order_item,
                index=source.index,
                batch_barcode=batch_primary_barcode(warehouse_item.batch)
                if warehouse_item.batch
                else None,
                origin_country=warehouse_item.origin_country,
                returned_warehouse_item=warehouse_item,
            )
            if source.amount > warehouse_item.amount:
                source.amount -= warehouse_item.amount
                source.save(update_fields=["amount", "changed"])
            else:
                source.delete()

        return warehouse_inbound_order_orm_to_schema(
            inbound_warehouse_orders_for_schema().get(code=code)
        )

    @classmethod
    def receive_returned_item(
        cls,
        line: InboundWarehouseOrderItem,
        receipt: InboundWarehouseOrder,
        location: WarehouseLocation,
        context: RequestContext,
    ) -> WarehouseItem:
        """
        Confirmation of a receipt line that points at a shipped item: the item
        is back in stock - the very same row, so its whole history stays attached.
        """
        assert line.returned_warehouse_item_id is not None
        warehouse_item = WarehouseItem.objects.select_for_update().get(
            pk=line.returned_warehouse_item_id
        )
        assignment = warehouse_item.live_outbound_assignment
        if assignment is None or assignment.warehouse_order.order_id != (
            receipt.return_order_id
        ):
            raise WarehouseGenericError(
                f"Item {warehouse_item.pk} is no longer out of the warehouse "
                f"for '{receipt.code}'."
            )
        before = {
            "location": warehouse_item.location_id,
            "order_in": warehouse_item.order_in_id,
            "outbound_order": assignment.warehouse_order.code,
        }
        assignment.returned_at = timezone.now()
        assignment.save(update_fields=["returned_at", "changed"])

        warehouse_item.location = location
        warehouse_item.order_in = receipt
        # the row that brought the item back into stock (origin comes along on the row)
        warehouse_item.source_order_item = line
        warehouse_item.save(
            update_fields=["location", "order_in", "source_order_item", "changed"]
        )
        audit_service.add_entry(
            warehouse_item,
            action=AuditAction.UPDATE,
            user=context.user_id,
            reason=AuditMessages.ITEM_RETURNED_BY_CUSTOMER.CS.format(
                receipt_code=receipt.code
            ),
            changes={
                "location": {"old": before["location"], "new": location.pk},
                "order_in": {"old": before["order_in"], "new": receipt.pk},
                "returned_from_order": before["outbound_order"],
            },
        )
        WarehouseMovement.objects.create(
            location_from=None,
            location_to=location,
            inbound_order_code=receipt,
            stock_product=warehouse_item.stock_product,
            amount=warehouse_item.amount,
            item=warehouse_item,
            batch=warehouse_item.batch,
            worker=User.objects.get(pk=context.user_id) if context.user_id else None,
        )
        return warehouse_item


order_returns_service = OrderReturnsService()
