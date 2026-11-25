from django.db import models

from .base import BaseModel


class DocumentTarget(models.TextChoices):
    """Printable document kinds - each has (at most) one customised layout"""

    GOODS_RECEIPT = "goods_receipt", "Příjemka"
    ISSUE_NOTE = "issue_note", "Výdejka"
    DELIVERY_NOTE = "delivery_note", "Dodací list"
    OUTBOUND_INVOICE = "outbound_invoice", "Faktura vydaná"
    OFFER = "offer", "Nabídka"


class DocumentTemplate(BaseModel):
    """Customised layout of a document. No row => the built-in default layout."""

    target = models.CharField(
        max_length=32, choices=DocumentTarget.choices, unique=True
    )
    # which blocks / attributes the base template prints (see DocumentLayoutSchema)
    layout = models.JSONField()

    def __str__(self) -> str:
        return f"Document layout: {self.target}"
