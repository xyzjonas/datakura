from typing import cast

from django.db.models import Q, QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import IncomingOrdersPagination
from apps.warehouse.core.schemas.base import EmptyResponse
from apps.warehouse.core.schemas.orders import (
    IncomingOrderSchema,
    IncomingOrderItemCreateSchema,
    CreateIncomingOrderItemResponse,
    IncomingOrderCreateOrUpdateSchema,
    GetIncomingOrderResponse,
)
from apps.warehouse.core.services.orders import incoming_orders_service
from apps.warehouse.core.transformation import incoming_order_orm_to_schema
from apps.warehouse.models.orders import IncomingOrder

routes = Router(tags=["incoming_order"])


@routes.get("", response={200: list[IncomingOrderSchema]}, auth=None)
@paginate(IncomingOrdersPagination)
def get_incoming_orders(request: HttpRequest, search_term: str | None = None):
    """
    List incoming orders, optionally filtered by code or supplier name.
    """
    qs = cast(QuerySet[IncomingOrder], IncomingOrder.objects.select_related("supplier"))
    if search_term:
        search_term = search_term.lower()
        qs = qs.filter(
            Q(code__iexact=search_term)
            | Q(code__icontains=search_term)
            | Q(supplier__name__icontains=search_term)
        )

    return qs.all()


@routes.post("", response={200: GetIncomingOrderResponse}, auth=None)
def create_incoming_order(
    request: HttpRequest, params: IncomingOrderCreateOrUpdateSchema
):
    """
    Create an order
    """
    new_order = incoming_orders_service.update_or_create_incoming(params)
    return GetIncomingOrderResponse(data=new_order)


@routes.get("/{order_code}", response={200: GetIncomingOrderResponse}, auth=None)
def get_incoming_order(request: HttpRequest, order_code: str):
    """
    Retrieve a single incoming order by code.
    """
    return GetIncomingOrderResponse(
        data=incoming_order_orm_to_schema(IncomingOrder.objects.get(code=order_code))
    )


@routes.put("/{order_code}", response={200: GetIncomingOrderResponse}, auth=None)
def update_incoming_order(
    request: HttpRequest, order_code: str, params: IncomingOrderCreateOrUpdateSchema
):
    """
    Update an order
    """
    updated_order = incoming_orders_service.update_or_create_incoming(
        params, code=order_code
    )
    return GetIncomingOrderResponse(data=updated_order)


@routes.post(
    "/{order_code}/items", response={200: CreateIncomingOrderItemResponse}, auth=None
)
def add_item_to_incoming_order(
    request: HttpRequest, order_code: str, item: IncomingOrderItemCreateSchema
):
    """
    Retrieve a single incoming order by code.
    """
    new_item = incoming_orders_service.add_item(order_code, item)
    return CreateIncomingOrderItemResponse(data=new_item)


@routes.delete(
    "/{order_code}/items/{product_code}", response={200: EmptyResponse}, auth=None
)
def remove_items_from_incoming_order(
    request: HttpRequest, order_code: str, product_code: str
):
    """
    Retrieve a single incoming order by code.
    """
    result = incoming_orders_service.remove_item(order_code, product_code)
    return EmptyResponse(success=result)
