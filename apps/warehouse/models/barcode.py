from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import TextChoices
from django.db import models

from .base import BaseModel


class BarcodeType(TextChoices):
    EAN13 = "EAN13", "EAN-13"
    EAN8 = "EAN8", "EAN-8"
    UPC = "UPC", "UPC"
    GS1_128 = "GS1_128", "GS1-128"
    QR = "QR", "QR Code"
    SERIAL = "SERIAL", "Serial Number"
    SSCC = "SSCC", "SSCC"
    CUSTOM = "CUSTOM", "Custom"


class Barcode(BaseModel):
    """Flexible barcode mapping"""

    code = models.CharField(max_length=100, unique=True, db_index=True)

    barcode_type = models.CharField(max_length=10, choices=BarcodeType.choices)
    # Polymorphic reference - barcode can point to different things
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    is_primary = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["content_type", "object_id"]),
        ]


# Now you can have:
# - Multiple EANs on StockProduct
# - Batch-specific barcodes on Batch
# - Serial codes on SerializedItem
# - Even location barcodes, bin barcodes, etc.


# Generic helper
def attach_barcode(
    obj,
    code: str,
    barcode_type: BarcodeType = BarcodeType.EAN13,
    is_primary: bool = False,
) -> Barcode:
    ct = ContentType.objects.get_for_model(obj)

    # Enforce only one primary per object
    if is_primary:
        Barcode.objects.filter(
            content_type=ct, object_id=obj.pk, is_primary=True
        ).update(is_primary=False)

    barcode, created = Barcode.objects.get_or_create(
        code=code,
        defaults={
            "content_type": ct,
            "object_id": obj.pk,
            "barcode_type": barcode_type,
            "is_primary": is_primary,
        },
    )

    if not created and barcode.content_object != obj:
        raise ValueError(f"Barcode {code} already assigned to {barcode.content_object}")

    return barcode


class BarcodeMixin(models.Model):
    class Meta:
        abstract = True

    def attach_barcode(
        self,
        code: str,
        barcode_type: BarcodeType = BarcodeType.EAN13,
        is_primary: bool = False,
    ) -> Barcode:
        return attach_barcode(self, code, barcode_type, is_primary)

    def get_barcodes(self):
        ct = ContentType.objects.get_for_model(self)
        return Barcode.objects.filter(content_type=ct, object_id=self.pk)

    def get_primary_barcode(self) -> Barcode | None:
        return self.get_barcodes().filter(is_primary=True).first()
