from __future__ import annotations

from typing import cast

from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import ProductGroupPagination
from apps.warehouse.core.schemas.group import (
    GetProductGroupResponse,
    ProductGroupSchema,
    ProductGroupCreateOrUpdateSchema,
)
from apps.warehouse.core.transformation import product_group_orm_to_schema
from apps.warehouse.models.product import ProductGroup

routes = Router(tags=["groups"])


@routes.get("", response={200: list[ProductGroupSchema]})
@paginate(ProductGroupPagination)
def get_groups(request: HttpRequest, search_term: str | None = None):
    qs = cast(QuerySet[ProductGroup], ProductGroup.objects.all())
    if search_term:
        search_term = search_term.lower()
        qs = qs.filter(name__icontains=search_term)

    return qs.all()


@routes.post("", response={200: GetProductGroupResponse})
def create_group(request: HttpRequest, body: ProductGroupCreateOrUpdateSchema):
    group, _ = ProductGroup.objects.get_or_create(name=body.name)
    return GetProductGroupResponse(data=product_group_orm_to_schema(group))


@routes.put("/{group_name}", response={200: GetProductGroupResponse})
def update_group(
    request: HttpRequest,
    group_name: str,
    body: ProductGroupCreateOrUpdateSchema,
):
    group = ProductGroup.objects.get(name=group_name)
    group.name = body.name
    group.save()
    return GetProductGroupResponse(data=product_group_orm_to_schema(group))
