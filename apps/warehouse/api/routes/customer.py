from __future__ import annotations

from typing import cast

from django.db.models import Q, QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import CustomersPagination
from apps.warehouse.core.schemas.base import BaseResponse
from apps.warehouse.core.schemas.customer import (
    GetCustomerResponse,
    CustomerSchema,
)
from apps.warehouse.core.transformation import customer_orm_to_schema
from apps.warehouse.models.customer import Customer

routes = Router(tags=["customers"])


@routes.get("", response={200: list[CustomerSchema], 404: BaseResponse}, auth=None)
@paginate(CustomersPagination)
def get_customers(
    request: HttpRequest,
    search_term: str | None = None,
    is_deleted: bool = False,
    is_active: bool = True,
):
    qs = cast(
        QuerySet[Customer],
        Customer.objects.filter(is_deleted=is_deleted, is_valid=is_active),
    )
    if not search_term:
        return qs.all()

    try:
        qs.get(code=search_term)
    except Customer.DoesNotExist:
        pass

    search_term = search_term.lower()
    qs = qs.filter(Q(code__icontains=search_term) | Q(name__icontains=search_term))
    return qs.all()


@routes.get("/{customer_code}", response={200: GetCustomerResponse}, auth=None)
def get_customer(request: HttpRequest, customer_code: str):
    customer = Customer.objects.prefetch_related(
        "contacts", "customer_group", "responsible_user", "owner"
    ).get(code=customer_code)
    return GetCustomerResponse(data=customer_orm_to_schema(customer))
