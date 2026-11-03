from __future__ import annotations

from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import ShippingTypePagination
from apps.warehouse.core.schemas.base import EmptyResponse
from apps.warehouse.core.schemas.shipping import (
    GetShippingTypeResponse,
    ShippingTypeCreateOrUpdateSchema,
    ShippingTypeSchema,
)
from apps.warehouse.core.services.shipping import shipping_service
from apps.warehouse.core.transformation import shipping_type_orm_to_schema

routes = Router(tags=["shipping_type"])


@routes.get("", response={200: list[ShippingTypeSchema]})
@paginate(ShippingTypePagination)
def get_shipping_types(request: HttpRequest, search_term: str | None = None):
    return shipping_service.get_shipping_types(search_term)


@routes.post("", response={200: GetShippingTypeResponse})
def create_shipping_type(request: HttpRequest, body: ShippingTypeCreateOrUpdateSchema):
    return GetShippingTypeResponse(
        data=shipping_type_orm_to_schema(shipping_service.create_shipping_type(body))
    )


@routes.put("/{type_id}", response={200: GetShippingTypeResponse})
def update_shipping_type(
    request: HttpRequest, type_id: int, body: ShippingTypeCreateOrUpdateSchema
):
    return GetShippingTypeResponse(
        data=shipping_type_orm_to_schema(
            shipping_service.update_shipping_type(type_id, body)
        )
    )


@routes.delete("/{type_id}", response={200: EmptyResponse})
def delete_shipping_type(request: HttpRequest, type_id: int):
    shipping_service.delete_shipping_type(type_id)
    return EmptyResponse(success=True)
