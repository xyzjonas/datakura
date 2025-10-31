from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from django.db import models
from django.db.models import QuerySet

from .base import BaseModel


STATE_CHOICES = [
    ("CZ", "Czech Republic"),
    ("SK", "Slovakia"),
    # Add more countries as needed
]


class CustomerGroup(BaseModel):
    """Customer group classification"""

    code = models.CharField(max_length=100, unique=True, null=False)
    name = models.CharField(max_length=255, null=False)

    def __str__(self):
        return self.name


class Customer(BaseModel):
    """Main customer model"""

    PRICE_TYPE_CHOICES = [
        ("FIRMY", "Companies"),
        # Add more price types as needed
    ]

    CUSTOMER_TYPE_CHOICES = [
        ("FIRMA", "Company"),
        ("OSOBA", "Person"),
        # Add more price types as needed
    ]

    # Basic Information
    name = models.CharField(max_length=255)
    email = models.EmailField(validators=[EmailValidator()], blank=True)
    phone = models.CharField(max_length=50, blank=True)
    code = models.CharField(max_length=50, unique=True)

    # Address
    street = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    state = models.CharField(max_length=50, choices=STATE_CHOICES, default="CZ")

    # Tax Information
    tax_identification = models.CharField(max_length=50, blank=True)
    identification = models.CharField(max_length=50, blank=True)

    # Business Settings
    customer_type = models.CharField(max_length=50, choices=CUSTOMER_TYPE_CHOICES)
    price_type = models.CharField(max_length=50, choices=PRICE_TYPE_CHOICES)
    invoice_due_days = models.IntegerField(default=30)
    block_after_due_days = models.IntegerField(default=30)

    # Agreements
    data_collection_agreement = models.BooleanField(default=False)
    marketing_data_use_agreement = models.BooleanField(default=False)

    # Status Fields
    is_valid = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    # Relationships
    owner = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_customers",
    )
    responsible_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="responsible_for",
    )
    customer_group = models.ForeignKey(
        CustomerGroup, on_delete=models.PROTECT, related_name="customers"
    )
    contacts: QuerySet["ContactPerson"]

    # Additional Fields
    note = models.TextField(blank=True, null=True)
    register_information = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    def get_full_address(self):
        """Return formatted full address"""
        parts = [self.street, f"{self.postal_code} {self.city}".strip(), self.state]
        return ", ".join(filter(None, parts))


class ContactPerson(BaseModel):
    """Contact person associated with customer"""

    # Name components
    title_pre = models.CharField(max_length=50, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    title_post = models.CharField(max_length=50, blank=True, null=True)

    # Contact information
    email = models.EmailField(validators=[EmailValidator()], blank=True)
    phone = models.CharField(max_length=50, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    # Address (Person can have their own address)
    street = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    state = models.CharField(max_length=2, choices=STATE_CHOICES, blank=True, null=True)

    # Relationships
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="contacts"
    )

    # Profile picture
    profile_picture_url = models.CharField(max_length=255, null=True, blank=True)

    # Status
    is_deleted = models.BooleanField(default=False)

    # Additional
    note = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Customer contact"
        verbose_name_plural = "Customer contacts"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        """Return formatted full name with titles"""
        parts = [
            self.title_pre,
            self.first_name,
            self.middle_name,
            self.last_name,
            self.title_post,
        ]
        return " ".join(filter(None, parts))
