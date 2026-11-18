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

from django.db import transaction
from django.db.models import Sum

from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
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
from apps.warehouse.core.services.warehouse_order_factory import (
    WarehouseOrderKind,
    create_warehouse_order,
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
                OutboundOrderItem.objects.create(
                    order=order,
                    stock_product=source.stock_product,
                    amount=amount,
                    unit_price=source.unit_price,
                    total_price=total_price,
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


order_returns_service = OrderReturnsService()
