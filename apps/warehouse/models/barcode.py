from collections.abc import Iterable

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


_BARCODE_CACHE_ATTR = "_prefetched_barcodes"


def prefetch_barcodes(objs: Iterable["BarcodeMixin | None"]) -> None:
    """
    Load barcodes of all the given objects (even of mixed models) in one query per
    model, so `barcode_list()` / `get_primary_barcode()` don't hit the DB per object.

    Barcodes are a generic relation without a `GenericRelation` on the model (it would
    cascade deletes), hence `prefetch_related` can't do this.
    """
    by_model: dict[type, dict[int, BarcodeMixin]] = {}
    for obj in objs:
        if obj is None or getattr(obj, _BARCODE_CACHE_ATTR, None) is not None:
            continue
        by_model.setdefault(type(obj), {})[obj.pk] = obj

    for model, instances in by_model.items():
        for obj in instances.values():
            setattr(obj, _BARCODE_CACHE_ATTR, [])
        ct = ContentType.objects.get_for_model(model)
        for barcode in Barcode.objects.filter(
            content_type=ct, object_id__in=instances.keys()
        ).order_by("pk"):
            getattr(instances[barcode.object_id], _BARCODE_CACHE_ATTR).append(barcode)


class BarcodeQuerySet(models.QuerySet):
    """
    `.with_barcodes()` loads the barcodes of every fetched row in one extra query.
    Works inside `Prefetch(..., queryset=Model.objects.with_barcodes())` as well.
    """

    _with_barcodes = False

    def with_barcodes(self):
        clone = self._chain()
        clone._with_barcodes = True
        return clone

    def _clone(self):
        clone = super()._clone()
        clone._with_barcodes = self._with_barcodes
        return clone

    def _fetch_all(self):
        was_loaded = self._result_cache is not None
        super()._fetch_all()
        if self._with_barcodes and not was_loaded:
            prefetch_barcodes(self._result_cache)  # type: ignore[arg-type]


class BarcodeMixin(models.Model):
    class Meta:
        abstract = True

    objects = BarcodeQuerySet.as_manager()

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

    def barcode_list(self) -> list[Barcode]:
        """
        All barcodes as a list - served from `prefetch_barcodes()` if it ran for this
        instance (no query), otherwise fetched (and not cached).
        """
        cached = getattr(self, _BARCODE_CACHE_ATTR, None)
        if cached is not None:
            return cached
        return list(self.get_barcodes())

    def get_primary_barcode(self) -> Barcode | None:
        cached = getattr(self, _BARCODE_CACHE_ATTR, None)
        if cached is not None:
            return next((b for b in cached if b.is_primary), None)
        return self.get_barcodes().filter(is_primary=True).first()
