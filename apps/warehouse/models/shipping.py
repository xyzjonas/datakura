from __future__ import annotations

from django.db import models

from .base import BaseModel
from .customer import STATE_CHOICES
from .orders import OutboundOrder


UNKNOWN_SHIPPING_TYPE_NAME = "Neurčeno"
# Highest possible 32-bit key keeps the low ids free for the user created types
UNKNOWN_SHIPPING_TYPE_ID = 2**31 - 1


class ShippingType(BaseModel):
    """
    Way of transport, e.g. "Balík PPL".

    One sentinel row ("unknown", `UNKNOWN_SHIPPING_TYPE_ID`) is the default of every
    shipping that has no type chosen yet. It is hidden from the API and read-only.
    """

    name = models.CharField(max_length=100, unique=True)

    class Meta(BaseModel.Meta):
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_unknown(self) -> bool:
        return self.pk == UNKNOWN_SHIPPING_TYPE_ID

    @staticmethod
    def get_unknown() -> int:
        """Id of the sentinel type (created on demand); usable as a field default."""
        return ShippingType.objects.get_or_create(
            id=UNKNOWN_SHIPPING_TYPE_ID,
            defaults={"name": UNKNOWN_SHIPPING_TYPE_NAME},
        )[0].id

    @classmethod
    def resolve(cls, name: str | None) -> "ShippingType | None":
        """Get or create a shipping type by name; blank name means none."""
        normalized_name = (name or "").strip()
        if not normalized_name:
            return None
        return cls.objects.get_or_create(name=normalized_name)[0]


class OutboundOrderShipping(BaseModel):
    """
    Where and how an `OutboundOrder` is shipped. Exactly one per order: it is created
    together with the order (see `signals.py`), possibly empty (type = the
    "unknown" sentinel), and never deleted on its own.

    The address is a snapshot seeded from `OutboundOrder.contact` (overridable);
    it is rewritten whenever the order's contact changes. The weight is not stored,
    it is always derived from the order items.
    """

    order = models.OneToOneField(
        OutboundOrder, on_delete=models.CASCADE, related_name="shipping"
    )
    shipping_type = models.ForeignKey(
        ShippingType,
        on_delete=models.PROTECT,
        related_name="shippings",
        default=ShippingType.get_unknown,
    )
    package_number = models.CharField(max_length=100, blank=True, default="")

    # package dimensions
    width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    depth = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # address
    name = models.CharField(max_length=255, blank=True, default="")
    state = models.CharField(
        max_length=2, choices=STATE_CHOICES, blank=True, default="CZ"
    )
    city = models.CharField(max_length=100, blank=True, default="")
    street = models.CharField(max_length=255, blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    email = models.CharField(max_length=254, blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")

    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_with_vat = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    class Meta(BaseModel.Meta):
        verbose_name_plural = "Outbound order shippings"

    def __str__(self) -> str:
        return f"{self.order.code} | {self.shipping_type}"
