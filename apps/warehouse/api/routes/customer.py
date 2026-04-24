from __future__ import annotations

from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import CustomersPagination
from apps.warehouse.core.schemas.base import BaseResponse
from apps.warehouse.core.schemas.customer import (
    GetCustomerResponse,
    CustomerSchema,
    CustomerDiscountGroupAssignSchema,
    CustomerCreateOrUpdateSchema,
    ContactPersonCreateOrUpdateSchema,
    ContactPersonSchema,
)
from apps.warehouse.core.transformation import customer_orm_to_schema
from apps.warehouse.core.services.customers import (
    customer_service,
    contact_person_service,
)
from apps.warehouse.models.customer import Customer, ContactPerson
from apps.warehouse.models.product import PriceGroup

routes = Router(tags=["customers"])


# ============ CUSTOMER ENDPOINTS ============


@routes.get("", response={200: list[CustomerSchema], 404: BaseResponse})
@paginate(CustomersPagination)
def get_customers(
    request: HttpRequest,
    search_term: str | None = None,
    is_deleted: bool = False,
    is_active: bool = True,
    is_self: bool | None = None,
):
    return customer_service.list_customers(
        search_term=search_term,
        is_deleted=is_deleted,
        is_active=is_active,
        is_self=is_self,
    )


@routes.post("", response={200: GetCustomerResponse})
def create_customer(request: HttpRequest, body: CustomerCreateOrUpdateSchema):
    """Create a new customer"""
    result = customer_service.create_customer(body)
    return GetCustomerResponse(data=result)


@routes.get("/self", response={200: GetCustomerResponse})
def get_self_customer(request: HttpRequest):
    return GetCustomerResponse(data=customer_service.get_self_customer())


@routes.get("/{customer_code}", response={200: GetCustomerResponse})
def get_customer(request: HttpRequest, customer_code: str):
    customer = (
        Customer.objects.select_related(
            "customer_group",
            "discount_group",
            "responsible_user",
            "owner",
            "default_payment_method",
        )
        .prefetch_related("contacts")
        .get(code=customer_code)
    )
    return GetCustomerResponse(data=customer_orm_to_schema(customer))


@routes.put("/{customer_code}", response={200: GetCustomerResponse})
def update_customer(
    request: HttpRequest,
    customer_code: str,
    body: CustomerCreateOrUpdateSchema,
):
    """Update an existing customer"""
    result = customer_service.update_customer(customer_code, body)
    return GetCustomerResponse(data=result)


@routes.delete("/{customer_code}", response={200: GetCustomerResponse})
def delete_customer(request: HttpRequest, customer_code: str):
    """Delete a customer (soft delete)"""
    result = customer_service.delete_customer(customer_code)
    return GetCustomerResponse(data=result)


@routes.patch("/{customer_code}/discount-group", response={200: GetCustomerResponse})
def assign_customer_discount_group(
    request: HttpRequest,
    customer_code: str,
    body: CustomerDiscountGroupAssignSchema,
):
    customer = Customer.objects.get(code=customer_code)
    if body.discount_group_code:
        customer.discount_group = PriceGroup.objects.get(code=body.discount_group_code)
    else:
        customer.discount_group = None
    customer.save(update_fields=["discount_group", "changed"])

    customer = (
        Customer.objects.select_related(
            "customer_group",
            "discount_group",
            "responsible_user",
            "owner",
            "default_payment_method",
        )
        .prefetch_related("contacts")
        .get(code=customer_code)
    )
    return GetCustomerResponse(data=customer_orm_to_schema(customer))


# ============ CONTACT PERSON ENDPOINTS ============


@routes.get(
    "/{customer_code}/contacts",
    response={200: list[ContactPersonSchema]},
)
def get_customer_contacts(request: HttpRequest, customer_code: str):
    """Get all contact persons for a customer"""
    contacts = ContactPerson.objects.filter(
        customer__code=customer_code, is_deleted=False
    ).order_by("last_name", "first_name")
    return [ContactPersonSchema.from_orm(c) for c in contacts]


@routes.post(
    "/{customer_code}/contacts",
    response={200: ContactPersonSchema},
)
def create_customer_contact(
    request: HttpRequest,
    customer_code: str,
    body: ContactPersonCreateOrUpdateSchema,
):
    """Create a new contact person for a customer"""
    contact = contact_person_service.create_contact_person(customer_code, body)
    return contact


@routes.put(
    "/{customer_code}/contacts/{contact_id}",
    response={200: ContactPersonSchema},
)
def update_customer_contact(
    request: HttpRequest,
    customer_code: str,
    contact_id: int,
    body: ContactPersonCreateOrUpdateSchema,
):
    """Update a contact person"""
    contact = contact_person_service.update_contact_person(contact_id, body)
    return contact


@routes.delete(
    "/{customer_code}/contacts/{contact_id}",
    response={200: ContactPersonSchema},
)
def delete_customer_contact(
    request: HttpRequest,
    customer_code: str,
    contact_id: int,
):
    """Delete a contact person (soft delete)"""
    contact = contact_person_service.delete_contact_person(contact_id)
    return contact
