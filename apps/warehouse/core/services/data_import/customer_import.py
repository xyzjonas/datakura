"""Import of legacy customers (customer + contact people) from JSON"""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.warehouse.core.services.data_import.common import (
    parse_rows,
    read_text,
    validate_rows,
)
from apps.warehouse.core.services.data_import.errors import DataImportError
from apps.warehouse.core.services.data_import.progress import ImportProgress
from apps.warehouse.models.customer import (
    STATE_CHOICES,
    ContactPerson,
    Customer,
    CustomerGroup,
)

PROGRESS_EVERY = 1000
CUSTOMER_TYPE_MAP = {"COMPANY": "FIRMA", "PERSON": "OSOBA"}
_STATES = {code for code, _ in STATE_CHOICES}
_CUSTOMER_TYPES = {code for code, _ in Customer.CUSTOMER_TYPE_CHOICES}
DEFAULT_CUSTOMER_TYPE = "FIRMA"
DEFAULT_GROUP_CODE = "default"


def _blank_to_none(value: Any) -> Any:
    return None if isinstance(value, str) and not value.strip() else value


def code_from_name(name: Any) -> str:
    """ASCII-only code: spaces/dots -> dashes, other non-alphanumerics dropped"""
    if not isinstance(name, str):
        return ""
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    dashed = re.sub(r"[\s.]+", "-", ascii_name.strip())
    cleaned = re.sub(r"[^A-Za-z0-9-]", "", dashed)
    return re.sub(r"-{2,}", "-", cleaned).strip("-")[:50].upper()


def _known_state_or_none(value: str | None) -> str | None:
    return value if value in _STATES else None


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def drop_nulls(cls, data: Any) -> Any:
        """Null/blank input means "not provided" -> fall back to field default"""
        if isinstance(data, dict):
            return {
                key: value
                for key, value in data.items()
                if value is not None
                and not (isinstance(value, str) and not value.strip())
            }
        return data


class LegacyPerson(_Base):
    title_pre: str | None = Field(None, alias="TitlePre", max_length=50)
    first_name: str = Field("", alias="FirstName", max_length=100)
    middle_name: str | None = Field(None, alias="MiddleName", max_length=100)
    last_name: str = Field("", alias="LastName", max_length=100)
    title_post: str | None = Field(None, alias="TitlePost", max_length=50)
    email: str = Field("", alias="Email", max_length=254)
    phone: str = Field("", alias="Phone", max_length=50)
    birth_date: date | None = Field(None, alias="BirthDate")
    street: str | None = Field(None, alias="Street", max_length=255)
    city: str | None = Field(None, alias="City", max_length=100)
    postal_code: str | None = Field(None, alias="PostalCode", max_length=20)
    state: str | None = Field(None, alias="State")
    note: str | None = Field(None, alias="Note")

    @field_validator(
        "title_pre",
        "middle_name",
        "title_post",
        "birth_date",
        "street",
        "city",
        "postal_code",
        "state",
        "note",
        mode="before",
    )
    @classmethod
    def blank(cls, value):
        return _blank_to_none(value)

    @field_validator("email", "phone", mode="before")
    @classmethod
    def none_to_empty(cls, value):
        return "" if value is None else value

    _state = field_validator("state")(_known_state_or_none)

    @model_validator(mode="after")
    def name_falls_back_to_email(self):
        if not (self.first_name or self.last_name):
            self.first_name = self.email[:100]
        return self


class LegacyCustomer(_Base):
    code: str = Field(..., alias="Code", min_length=1, max_length=50)
    name: str = Field(..., alias="Name", min_length=1, max_length=255)
    email: str = Field("", alias="Email", max_length=254)
    phone: str = Field("", alias="Phone", max_length=50)
    street: str = Field("", alias="Street", max_length=255)
    city: str = Field("", alias="City", max_length=100)
    postal_code: str = Field("", alias="PostalCode", max_length=20)
    state: str = Field("CZ", alias="State", max_length=50)
    identification: str = Field("", alias="Identification", max_length=50)
    tax_identification: str = Field("", alias="TaxIdentification", max_length=50)
    register_information: str | None = Field(None, alias="RegisterInformation")
    note: str | None = Field(None, alias="Note")
    is_valid: bool = Field(True, alias="IsValid")
    is_deleted: bool = Field(False, alias="IsDeleted")
    data_collection_agreement: bool = Field(False, alias="DataCollectionAgreement")
    marketing_data_use_agreement: bool = Field(False, alias="MarketingDataUseAgreement")
    price_type: str = Field("", alias="PriceTypeCode", max_length=50)
    invoice_due_days: int = Field(14, alias="InvoiceDueDays", ge=0)
    block_after_due_days: int = Field(30, alias="BlockAfterDueDays", ge=0)
    responsible_user_email: str | None = Field(None, alias="ResponsibleUserEmail")
    customer_type: str = Field(DEFAULT_CUSTOMER_TYPE, alias="CustomerTypeCode")
    customer_group_code: str = Field(
        DEFAULT_GROUP_CODE, alias="CustomerGroupCode", max_length=100
    )
    people: list[LegacyPerson] = Field(default_factory=list, alias="People")

    @model_validator(mode="before")
    @classmethod
    def code_defaults_to_name(cls, data: Any) -> Any:
        if isinstance(data, dict) and _blank_to_none(data.get("Code")) is None:
            data = {**data, "Code": code_from_name(data.get("Name"))}
        return data

    @field_validator(
        "email",
        "phone",
        "street",
        "city",
        "postal_code",
        "identification",
        "tax_identification",
        mode="before",
    )
    @classmethod
    def none_to_empty(cls, value):
        return "" if value is None else value

    @field_validator(
        "register_information", "note", "responsible_user_email", mode="before"
    )
    @classmethod
    def blank(cls, value):
        return _blank_to_none(value)

    @field_validator("people", mode="before")
    @classmethod
    def none_to_list(cls, value):
        return [] if value is None else value

    @field_validator(
        "is_valid",
        "is_deleted",
        "data_collection_agreement",
        "marketing_data_use_agreement",
        mode="before",
    )
    @classmethod
    def none_to_false(cls, value):
        return False if value is None else value

    @field_validator("customer_type")
    @classmethod
    def map_customer_type(cls, value):
        mapped = CUSTOMER_TYPE_MAP.get(value, value)
        if mapped not in _CUSTOMER_TYPES:
            raise ValueError(f"Unsupported customer type '{value}'")
        return mapped


@dataclass
class CustomerImportSummary:
    created_count: int = 0
    updated_count: int = 0
    contacts_count: int = 0
    groups_created: int = 0
    users_created: int = 0
    warnings: list[str] = field(default_factory=list)


class CustomerImportService:
    def import_from_path(
        self, path: str | Path, progress: ImportProgress | None = None
    ) -> CustomerImportSummary:
        logger.info("Customer import: reading '{}'", path)
        return self.import_from_json(read_text(path), progress)

    def import_from_json(
        self, raw: str, progress: ImportProgress | None = None
    ) -> CustomerImportSummary:
        progress = progress or ImportProgress()
        rows = parse_rows(raw)
        logger.info("Customer import: parsed {} records", len(rows))
        progress.set_phase("validating")
        validated = validate_rows(LegacyCustomer, rows)
        progress.set_total(len(validated))
        return self._import_customers(validated, progress)

    @transaction.atomic
    def _import_customers(
        self, customers: list[tuple[int, LegacyCustomer]], progress: ImportProgress
    ) -> CustomerImportSummary:
        summary = CustomerImportSummary()
        errors: list[str] = []

        total = len(customers)
        for position, (index, customer) in enumerate(customers, start=1):
            progress.advance()
            if position % PROGRESS_EVERY == 0:
                logger.info("Customer import: processed {}/{}", position, total)
            try:
                with transaction.atomic():
                    created = self._import_customer(customer, summary)
            except Exception as exc:
                logger.error(
                    "Customer '{}' failed: {}: {}",
                    customer.code,
                    type(exc).__name__,
                    exc,
                )
                errors.append(f"Customer #{index} '{customer.code}': {exc}")
                continue

            logger.debug(
                "Customer '{}': {}", customer.code, "created" if created else "updated"
            )
            if created:
                summary.created_count += 1
            else:
                summary.updated_count += 1

        if errors:
            logger.error(
                "Customer import failed, rolling back: {} failing records", len(errors)
            )
            raise DataImportError("\n".join(errors))

        for warning in summary.warnings:
            logger.warning("Customer import: {}", warning)
        logger.info(
            "Customer import done: {} created, {} updated, {} contacts, "
            "{} new groups, {} new users, {} warnings",
            summary.created_count,
            summary.updated_count,
            summary.contacts_count,
            summary.groups_created,
            summary.users_created,
            len(summary.warnings),
        )
        return summary

    def _import_customer(
        self, customer: LegacyCustomer, summary: CustomerImportSummary
    ) -> bool:
        group, group_created = CustomerGroup.objects.get_or_create(
            code=customer.customer_group_code,
            defaults={"name": customer.customer_group_code},
        )
        summary.groups_created += group_created

        result, created = Customer.objects.update_or_create(
            code=customer.code,
            defaults={
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "street": customer.street,
                "city": customer.city,
                "postal_code": customer.postal_code,
                "state": customer.state,
                "identification": customer.identification,
                "tax_identification": customer.tax_identification,
                "register_information": customer.register_information,
                "note": customer.note,
                "is_valid": customer.is_valid,
                "is_deleted": customer.is_deleted,
                "data_collection_agreement": customer.data_collection_agreement,
                "marketing_data_use_agreement": customer.marketing_data_use_agreement,
                "price_type": customer.price_type,
                "customer_type": customer.customer_type,
                "invoice_due_days": customer.invoice_due_days,
                "block_after_due_days": customer.block_after_due_days,
                "customer_group": group,
                "responsible_user": self._find_user(customer, summary),
            },
        )

        for person in customer.people:
            if not (person.first_name or person.last_name):
                summary.warnings.append(
                    f"Customer '{customer.code}': contact without a name or email skipped"
                )
                continue
            ContactPerson.objects.update_or_create(
                customer=result,
                first_name=person.first_name,
                last_name=person.last_name,
                email=person.email,
                defaults=person.model_dump(
                    exclude={"first_name", "last_name", "email"}
                ),
            )
            summary.contacts_count += 1
        return created

    @staticmethod
    def _find_user(customer: LegacyCustomer, summary: CustomerImportSummary):
        email = customer.responsible_user_email
        if not email:
            return None

        user = User.objects.filter(email__iexact=email).order_by("pk").first()
        if user is None:
            user = User(username=email[:150], email=email)
            user.set_unusable_password()
            user.save()
            summary.users_created += 1
            logger.info("Created user '{}' for customer '{}'", email, customer.code)
        return user
