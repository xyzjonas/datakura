from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models import Q, QuerySet
from django.db import transaction

from apps.warehouse.core.exceptions import NotFoundException, WarehouseGenericError
from apps.warehouse.core.schemas.customer import (
    CustomerCreateOrUpdateSchema,
    ContactPersonCreateOrUpdateSchema,
)
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.core.transformation import customer_orm_to_schema
from apps.warehouse.models.customer import Customer, ContactPerson, CustomerGroup
from apps.warehouse.models.orders import InvoicePaymentMethod
from apps.warehouse.models.product import PriceGroup


class CustomerService:
    @staticmethod
    def _get_customer_queryset() -> QuerySet[Customer]:
        return Customer.objects.select_related(
            "customer_group",
            "discount_group",
            "responsible_user",
            "owner",
            "default_payment_method",
        ).prefetch_related("contacts")

    @staticmethod
    def list_customers(
        search_term: str | None = None,
        *,
        is_deleted: bool = False,
        is_active: bool = True,
        is_self: bool | None = None,
    ) -> QuerySet[Customer]:
        queryset = CustomerService._get_customer_queryset().filter(
            is_deleted=is_deleted,
            is_valid=is_active,
        )

        if is_self is not None:
            queryset = queryset.filter(is_self=is_self)

        if search_term:
            normalized_search_term = search_term.lower()
            queryset = queryset.filter(
                Q(code__icontains=normalized_search_term)
                | Q(name__icontains=normalized_search_term)
                | Q(tax_identification__icontains=normalized_search_term)
                | Q(identification__icontains=normalized_search_term)
            )

        return queryset.all()

    @staticmethod
    def get_self_customer():
        try:
            customer = CustomerService.list_customers(is_self=True).get()
        except Customer.DoesNotExist as exc:
            raise NotFoundException("Active self customer not found") from exc

        return customer_orm_to_schema(customer)

    @staticmethod
    def _get_owner_or_none(username: str | None) -> User | None:
        if not username:
            return None
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None

    @staticmethod
    def _get_customer_group(code: str):
        try:
            return CustomerGroup.objects.get(code=code)
        except CustomerGroup.DoesNotExist:
            raise WarehouseGenericError(f"Customer group with code '{code}' not found")

    @staticmethod
    def _get_discount_group(code: str | None):
        if not code:
            return None
        try:
            return PriceGroup.objects.get(code=code)
        except PriceGroup.DoesNotExist:
            raise WarehouseGenericError(
                f"Discount group (price group) with code '{code}' not found"
            )

    @staticmethod
    def _get_default_payment_method(name: str | None):
        normalized_name = (name or "").strip()
        if not normalized_name:
            return None
        return InvoicePaymentMethod.objects.get_or_create(name=normalized_name)[0]

    @staticmethod
    def _validate_self_customer(
        is_self: bool,
        is_deleted: bool,
        customer_id: int | None = None,
    ):
        if not is_self or is_deleted:
            return

        query = Customer.objects.filter(is_self=True, is_deleted=False)
        if customer_id is not None:
            query = query.exclude(pk=customer_id)

        if query.exists():
            raise WarehouseGenericError(
                "Only one active customer can be marked as self"
            )

    @staticmethod
    @transaction.atomic
    def create_customer(params: CustomerCreateOrUpdateSchema):
        """Create a new customer"""
        # Check if customer with this code already exists
        if Customer.objects.filter(code=params.code).exists():
            raise WarehouseGenericError(
                f"Customer with code '{params.code}' already exists"
            )

        customer_group = CustomerService._get_customer_group(params.customer_group_code)
        discount_group = CustomerService._get_discount_group(params.discount_group_code)
        default_payment_method = CustomerService._get_default_payment_method(
            params.default_payment_method_name
        )
        owner = CustomerService._get_owner_or_none(params.owner)
        responsible_user = CustomerService._get_owner_or_none(params.responsible_user)
        CustomerService._validate_self_customer(params.is_self, params.is_deleted)

        customer = Customer.objects.create(
            name=params.name,
            email=params.email or "",
            phone=params.phone or "",
            code=params.code,
            street=params.street or "",
            city=params.city or "",
            postal_code=params.postal_code or "",
            state=params.state,
            tax_identification=params.tax_identification or "",
            identification=params.identification or "",
            customer_type=params.customer_type,
            price_type=params.price_type,
            invoice_due_days=params.invoice_due_days,
            block_after_due_days=params.block_after_due_days,
            is_self=params.is_self,
            data_collection_agreement=params.data_collection_agreement,
            marketing_data_use_agreement=params.marketing_data_use_agreement,
            is_valid=params.is_valid,
            is_deleted=params.is_deleted,
            customer_group=customer_group,
            discount_group=discount_group,
            default_payment_method=default_payment_method,
            owner=owner,
            responsible_user=responsible_user,
            note=params.note or "",
            register_information=params.register_information or "",
        )

        audit_service.add_entry(
            customer,
            action=AuditAction.CREATE,
            reason=AuditMessages.CUSTOMER_CREATED.CS,
        )

        # Fetch and return the customer with all relations
        customer = CustomerService._get_customer_queryset().get(code=customer.code)
        return customer_orm_to_schema(customer)

    @staticmethod
    @transaction.atomic
    def update_customer(customer_code: str, params: CustomerCreateOrUpdateSchema):
        """Update an existing customer"""
        customer = Customer.objects.get(code=customer_code)

        customer_group = CustomerService._get_customer_group(params.customer_group_code)
        discount_group = CustomerService._get_discount_group(params.discount_group_code)
        default_payment_method = CustomerService._get_default_payment_method(
            params.default_payment_method_name
        )
        owner = CustomerService._get_owner_or_none(params.owner)
        responsible_user = CustomerService._get_owner_or_none(params.responsible_user)
        CustomerService._validate_self_customer(
            params.is_self,
            params.is_deleted,
            customer_id=customer.pk,
        )

        # Update fields
        customer.name = params.name
        customer.email = params.email or ""
        customer.phone = params.phone or ""
        customer.code = params.code
        customer.street = params.street or ""
        customer.city = params.city or ""
        customer.postal_code = params.postal_code or ""
        customer.state = params.state
        customer.tax_identification = params.tax_identification or ""
        customer.identification = params.identification or ""
        customer.customer_type = params.customer_type
        customer.price_type = params.price_type
        customer.invoice_due_days = params.invoice_due_days
        customer.block_after_due_days = params.block_after_due_days
        customer.is_self = params.is_self
        customer.data_collection_agreement = params.data_collection_agreement
        customer.marketing_data_use_agreement = params.marketing_data_use_agreement
        customer.is_valid = params.is_valid
        customer.is_deleted = params.is_deleted
        customer.customer_group = customer_group
        customer.discount_group = discount_group
        customer.default_payment_method = default_payment_method
        customer.owner = owner
        customer.responsible_user = responsible_user
        customer.note = params.note or ""
        customer.register_information = params.register_information or ""

        customer.save()

        audit_service.add_entry(
            customer,
            action=AuditAction.UPDATE,
            reason=AuditMessages.CUSTOMER_UPDATED.CS,
        )

        # Fetch and return the customer with all relations
        customer = CustomerService._get_customer_queryset().get(code=customer.code)
        return customer_orm_to_schema(customer)

    @staticmethod
    @transaction.atomic
    def delete_customer(customer_code: str):
        """Delete a customer (soft delete by marking as deleted)"""
        customer = Customer.objects.get(code=customer_code)
        customer.is_deleted = True
        customer.save()

        audit_service.add_entry(
            customer,
            action=AuditAction.UPDATE,
            reason=AuditMessages.CUSTOMER_UPDATED.CS,
        )

        # Fetch and return the customer with all relations
        customer = CustomerService._get_customer_queryset().get(code=customer.code)
        return customer_orm_to_schema(customer)


class ContactPersonService:
    @staticmethod
    @transaction.atomic
    def create_contact_person(
        customer_code: str, params: ContactPersonCreateOrUpdateSchema
    ):
        """Create a new contact person for a customer"""
        customer = Customer.objects.get(code=customer_code)

        contact = ContactPerson.objects.create(
            title_pre=params.title_pre or "",
            first_name=params.first_name,
            middle_name=params.middle_name or "",
            last_name=params.last_name,
            title_post=params.title_post or "",
            email=params.email or "",
            phone=params.phone or "",
            birth_date=params.birth_date,
            street=params.street or "",
            city=params.city or "",
            postal_code=params.postal_code or "",
            state=params.state or "",
            profile_picture_url=params.profile_picture_url or "",
            is_deleted=params.is_deleted,
            note=params.note or "",
            customer=customer,
        )

        audit_service.add_entry(
            contact,
            action=AuditAction.CREATE,
            reason=AuditMessages.CONTACT_PERSON_CREATED.CS,
        )

        return contact

    @staticmethod
    @transaction.atomic
    def update_contact_person(
        contact_id: int, params: ContactPersonCreateOrUpdateSchema
    ):
        """Update an existing contact person"""
        contact = ContactPerson.objects.get(id=contact_id)

        contact.title_pre = params.title_pre or ""
        contact.first_name = params.first_name
        contact.middle_name = params.middle_name or ""
        contact.last_name = params.last_name
        contact.title_post = params.title_post or ""
        contact.email = params.email or ""
        contact.phone = params.phone or ""
        contact.birth_date = params.birth_date
        contact.street = params.street or ""
        contact.city = params.city or ""
        contact.postal_code = params.postal_code or ""
        contact.state = params.state or ""
        contact.profile_picture_url = params.profile_picture_url or ""
        contact.is_deleted = params.is_deleted
        contact.note = params.note or ""

        contact.save()

        audit_service.add_entry(
            contact,
            action=AuditAction.UPDATE,
            reason=AuditMessages.CONTACT_PERSON_UPDATED.CS,
        )

        return contact

    @staticmethod
    @transaction.atomic
    def delete_contact_person(contact_id: int):
        """Delete a contact person (soft delete)"""
        contact = ContactPerson.objects.get(id=contact_id)
        contact.is_deleted = True
        contact.save()

        audit_service.add_entry(
            contact,
            action=AuditAction.UPDATE,
            reason=AuditMessages.CONTACT_PERSON_DELETED.CS,
        )

        return contact


customer_service = CustomerService()
contact_person_service = ContactPersonService()
