from apps.warehouse.core.services.orders import inbound_orders_service
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderState,
    CreditNoteState,
)
from apps.warehouse.models.warehouse import InboundWarehouseOrderState


class InboundService:
    def next(self):
        pass

    def previous(self):
        pass

    class WarehouseOrderTransition:
        @staticmethod
        def confirm_draft(code: str) -> None:
            warehouse_service.transition_order(code, InboundWarehouseOrderState.PENDING)
            inbound_order = InboundOrder.objects.get(warehouse_order__code=code)
            inbound_orders_service.transition_order(
                inbound_order.code, InboundOrderState.PUTAWAY
            )
            inbound_orders_service.transition_credit_note(
                inbound_order.credit_note.code, CreditNoteState.CONFIRMED
            )

        @staticmethod
        def reset_to_draft(code: str) -> None:
            warehouse_service.transition_order(code, InboundWarehouseOrderState.DRAFT)
            inbound_order = InboundOrder.objects.get(warehouse_order__code=code)
            inbound_orders_service.transition_order(
                inbound_order.code, InboundOrderState.RECEIVING
            )
            inbound_orders_service.transition_credit_note(
                inbound_order.credit_note.code, CreditNoteState.DRAFT
            )
