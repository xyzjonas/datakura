from django.db import models

from .base import BaseModel


class DocumentTarget(models.TextChoices):
    """Printable document kinds - each has (at most) one customised template"""

    GOODS_RECEIPT = "goods_receipt", "Příjemka"
    ISSUE_NOTE = "issue_note", "Výdejka"
    DELIVERY_NOTE = "delivery_note", "Dodací list"
    OUTBOUND_INVOICE = "outbound_invoice", "Faktura vydaná"
    OFFER = "offer", "Nabídka"


class DocumentTemplate(BaseModel):
    """Customised (Jinja2 HTML) template of a document. No row => built-in default."""

    target = models.CharField(
        max_length=32, choices=DocumentTarget.choices, unique=True
    )
    # raw template source, stored verbatim
    content = models.TextField()

    def __str__(self) -> str:
        return f"Template: {self.target}"
