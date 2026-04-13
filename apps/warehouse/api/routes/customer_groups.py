from __future__ import annotations

from typing import cast

from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import CustomerGroupsPagination
from apps.warehouse.core.schemas.customer import (
    CustomerGroupSchema,
    CustomerGroupCreateOrUpdateSchema,
    GetCustomerGroupResponse,
)
from apps.warehouse.core.services.customer_groups import customer_groups_service
from apps.warehouse.models.customer import CustomerGroup

routes = Router(tags=["customer-groups"])


@routes.get("", response={200: list[CustomerGroupSchema]})
@paginate(CustomerGroupsPagination)
def get_customer_groups(request: HttpRequest, search_term: str | None = None):
    qs = cast(QuerySet[CustomerGroup], CustomerGroup.objects.all())
    if search_term:
        qs = qs.filter(name__icontains=search_term)
    return qs.order_by("name", "code")


@routes.post("", response={200: GetCustomerGroupResponse})
def create_customer_group(
    request: HttpRequest, body: CustomerGroupCreateOrUpdateSchema
):
    return GetCustomerGroupResponse(data=customer_groups_service.create_group(body))


@routes.put("/{group_code}", response={200: GetCustomerGroupResponse})
def update_customer_group(
    request: HttpRequest,
    group_code: str,
    body: CustomerGroupCreateOrUpdateSchema,
):
    return GetCustomerGroupResponse(
        data=customer_groups_service.update_group(group_code, body)
    )


@routes.delete("/{group_code}", response={200: GetCustomerGroupResponse})
def delete_customer_group(request: HttpRequest, group_code: str):
    return GetCustomerGroupResponse(
        data=customer_groups_service.delete_group(group_code)
    )
