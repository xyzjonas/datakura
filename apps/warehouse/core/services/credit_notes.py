"""Credit notes to customers (dobropis) - issued for goods taken back."""

from django.db import transaction
from loguru import logger

from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.credit_notes import CreditNoteSupplierSchema
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.transformation import credit_note_supplier_orm_to_schema
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.orders import (
    CreditNoteState,
    CreditNoteToCustomer,
    CreditNoteToSupplier,
)


class CreditNotesService:
    @staticmethod
    def get_credit_note(code: str) -> CreditNoteSupplierSchema:
        """Detail of a credit note, towards a supplier or a customer alike."""
        supplier_note = CreditNoteToSupplier.objects.filter(code=code).first()
        if supplier_note is not None:
            return credit_note_supplier_orm_to_schema(supplier_note)
        return credit_note_supplier_orm_to_schema(
            CreditNoteToCustomer.objects.get(code=code)
        )

    @staticmethod
    def transition_customer_credit_note(
        code: str, new_state: CreditNoteState, context: RequestContext
    ) -> None:
        note = CreditNoteToCustomer.objects.get(code=code)
        with transaction.atomic():
            old_state = note.state
            note.state = new_state
            note.save()
            logger.info(
                f"Credit note '{note.code}' transitioned: {old_state} -> {new_state}"
            )
            audit_service.add_entry(
                note,
                user=context.user_id,
                action=AuditAction.TRANSITION,
                reason=AuditMessages.CREDIT_NOTE_STATE_CHANGED.CS.format(
                    old_state=old_state, new_state=new_state
                ),
                changes={"state": {"old": old_state, "new": new_state}},
            )


credit_notes_service = CreditNotesService()
