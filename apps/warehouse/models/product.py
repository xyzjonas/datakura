"""Models related to the stock itself (items, packaging, etc...)"""

from collections.abc import Iterable
from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.utils import timezone

from .base import BaseModel
from .barcode import BarcodeMixin
from .currency import CURRENCY_CHOICES
from .packaging import UnitOfMeasure


class ProductType(BaseModel):
    """Catalogue of all possible product types"""

    name = models.CharField(max_length=255, null=False, unique=True)
    non_physical = models.BooleanField(
        default=False,
        help_text=(
            "Products of this type (services, fees, ...) are never picked: they stay "
            "in the base order for invoicing only and create no warehouse items."
        ),
    )

    def __str__(self) -> str:
        return self.name


class ProductGroup(BaseModel):
    """Grouping of products"""

    name = models.CharField(max_length=255, null=False, unique=True)
    parent = models.ForeignKey(
        "ProductGroup",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )

    def __str__(self) -> str:
        return self.name


class NormType(models.TextChoices):
    """Namespaces (standardization bodies) a norm code lives in"""

    ISO = "ISO", "ISO"
    CSN = "CSN", "ČSN"
    DIN = "DIN", "DIN"
    EN = "EN", "EN"


class Norm(BaseModel):
    """
    Catalogue of norms (DIN 84, ISO 1207, ...). A code is unique within its type;
    equal items defined by different norms are linked as `equivalents`.
    """

    code = models.CharField(max_length=64)
    type = models.CharField(max_length=8, choices=NormType.choices)
    equivalents = models.ManyToManyField("self", symmetrical=True, blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["type", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["type", "code"], name="warehouse_unique_norm_code_per_type"
            ),
            models.CheckConstraint(
                condition=~Q(code=""), name="warehouse_norm_code_not_empty"
            ),
        ]

    @property
    def label(self) -> str:
        return f"{self.type} {self.code}"

    def __str__(self) -> str:
        return self.label


class StockProduct(BaseModel, BarcodeMixin):
    name = models.CharField(max_length=255, null=False)
    code = models.CharField(max_length=255, null=False, unique=True)
    type = models.ForeignKey(ProductType, null=False, on_delete=models.PROTECT)
    group = models.ForeignKey(
        ProductGroup, null=True, blank=True, on_delete=models.SET_NULL
    )
    unit_of_measure = models.ForeignKey(
        UnitOfMeasure,
        null=False,
        on_delete=models.PROTECT,
        related_name="products",
    )
    unit_weight = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CZK")
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # bumped automatically by `save()` whenever the respective price changes
    purchase_price_changed = models.DateTimeField(default=timezone.now)
    base_price_changed = models.DateTimeField(default=timezone.now)
    no_discount = models.BooleanField(default=False)
    disallow_unpacking = models.BooleanField(
        default=False, help_text="Prevent unpacking packages during outbound picking"
    )

    customs_declaration_group = models.CharField(max_length=255, null=True, blank=True)
    norm = models.ForeignKey(
        Norm,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="products",
    )

    attributes = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta, BarcodeMixin.Meta):
        ordering = ["code"]

    # price field -> field holding the time of its last change
    PRICE_TIMESTAMP_FIELDS = {
        "purchase_price": "purchase_price_changed",
        "base_price": "base_price_changed",
    }

    def __str__(self):
        return self.name

    @staticmethod
    def _normalize_price(value) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value)).quantize(Decimal("0.01"))

    def _snapshot_prices(self) -> None:
        """Remember the persisted prices (skipping deferred ones)."""
        self._persisted_prices = {
            field: self._normalize_price(self.__dict__[field])
            for field in self.PRICE_TIMESTAMP_FIELDS
            if field in self.__dict__
        }

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._snapshot_prices()
        return instance

    def save(self, *args, update_fields=None, **kwargs):
        persisted = getattr(self, "_persisted_prices", {})
        now = timezone.now()
        touched: list[str] = []
        for field, timestamp_field in self.PRICE_TIMESTAMP_FIELDS.items():
            if field not in persisted:
                continue
            if self._normalize_price(getattr(self, field)) != persisted[field]:
                setattr(self, timestamp_field, now)
                touched.append(timestamp_field)
        if update_fields is not None:
            update_fields = [*update_fields, *touched]
        super().save(*args, update_fields=update_fields, **kwargs)
        self._snapshot_prices()


class PriceGroup(BaseModel):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(
                condition=Q(discount_percent__gte=0) & Q(discount_percent__lte=100),
                name="warehouse_pricegroup_discount_range",
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name} ({self.discount_percent}%)"


class StockProductPrice(BaseModel):
    product = models.ForeignKey(
        StockProduct,
        null=False,
        on_delete=models.CASCADE,
        related_name="dynamic_prices",
    )
    fixed_price = models.DecimalField(max_digits=10, decimal_places=2)
    customer = models.ForeignKey(
        "warehouse.Customer",
        null=False,
        on_delete=models.CASCADE,
        related_name="product_prices",
    )
    min_amount = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Minimum ordered amount for the price to be valid (empty = no limit)",
    )

    class Meta(BaseModel.Meta):
        ordering = ["product", "customer", "min_amount", "fixed_price"]
        constraints = [
            models.CheckConstraint(
                condition=Q(fixed_price__gte=0),
                name="warehouse_productprice_fixed_price_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(customer__isnull=False),
                name="warehouse_productprice_customer_required",
            ),
            models.CheckConstraint(
                condition=Q(min_amount__isnull=True) | Q(min_amount__gt=0),
                name="warehouse_productprice_min_amount_positive",
            ),
            models.UniqueConstraint(
                fields=["product", "customer", "min_amount"],
                condition=Q(min_amount__isnull=False),
                name="warehouse_unique_product_customer_min_amount_price",
            ),
            models.UniqueConstraint(
                fields=["product", "customer"],
                condition=Q(min_amount__isnull=True),
                name="warehouse_unique_product_customer_discount",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.code} - {self.customer.code} ({self.fixed_price})"


class CustomerProductCode(BaseModel):
    """The code a customer uses for one of our stock products (instead of our own)."""

    product = models.ForeignKey(
        StockProduct,
        null=False,
        on_delete=models.CASCADE,
        related_name="customer_codes",
    )
    customer = models.ForeignKey(
        "warehouse.Customer",
        null=False,
        on_delete=models.CASCADE,
        related_name="product_codes",
    )
    code = models.CharField(max_length=100)

    class Meta(BaseModel.Meta):
        ordering = ["product", "customer"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "customer"],
                name="warehouse_unique_customer_code_per_product",
            ),
            models.CheckConstraint(
                condition=~Q(code=""),
                name="warehouse_customer_product_code_not_empty",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.customer_id}: {self.product_id} -> {self.code}"

    @classmethod
    def codes_for(cls, customer, product_ids: Iterable[int]) -> dict[int, str]:
        """`{product id: customer's code}` of the given products (one query)."""
        return dict(
            cls.objects.filter(
                customer=customer, product_id__in=set(product_ids)
            ).values_list("product_id", "code")
        )
