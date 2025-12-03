from typing import cast

from django.db.models import Q, QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import IncomingOrdersPagination
from apps.warehouse.core.schemas.base import EmptyResponse
from apps.warehouse.core.schemas.orders import (
    InboundOrderSchema,
    InboundOrderItemCreateSchema,
    CreateInboundOrderItemResponse,
    InboundOrderCreateOrUpdateSchema,
    GetInboundOrderResponse,
    InboundOrderTransitionSchema,
)
from apps.warehouse.core.services.orders import inbound_orders_service
from apps.warehouse.core.transformation import inbound_order_orm_to_schema
from apps.warehouse.models.orders import InboundOrder

routes = Router(tags=["incoming_order"])


@routes.get("", response={200: list[InboundOrderSchema]}, auth=None)
@paginate(IncomingOrdersPagination)
def get_inbound_orders(request: HttpRequest, search_term: str | None = None):
    """
    List incoming orders, optionally filtered by code or supplier name.
    """
    qs = cast(QuerySet[InboundOrder], InboundOrder.objects.select_related("supplier"))
    if search_term:
        search_term = search_term.lower()
        qs = qs.filter(
            Q(code__iexact=search_term)
            | Q(code__icontains=search_term)
            | Q(supplier__name__icontains=search_term)
        )

    return qs.all()


@routes.post("", response={200: GetInboundOrderResponse}, auth=None)
def create_inbound_order(
    request: HttpRequest, params: InboundOrderCreateOrUpdateSchema
):
    """
    Create an order
    """
    new_order = inbound_orders_service.update_or_create_incoming(params)
    return GetInboundOrderResponse(data=new_order)


@routes.get("/{order_code}", response={200: GetInboundOrderResponse}, auth=None)
def get_inbound_order(request: HttpRequest, order_code: str):
    """
    Retrieve a single incoming order by code.
    """
    return GetInboundOrderResponse(
        data=inbound_order_orm_to_schema(InboundOrder.objects.get(code=order_code))
    )


@routes.put("/{order_code}", response={200: GetInboundOrderResponse}, auth=None)
def update_inbound_order(
    request: HttpRequest, order_code: str, params: InboundOrderCreateOrUpdateSchema
):
    """
    Update an order
    """
    updated_order = inbound_orders_service.update_or_create_incoming(
        params, code=order_code
    )
    return GetInboundOrderResponse(data=updated_order)


@routes.post(
    "/{order_code}/items", response={200: CreateInboundOrderItemResponse}, auth=None
)
def add_item_to_inbound_order(
    request: HttpRequest, order_code: str, item: InboundOrderItemCreateSchema
):
    """
    Retrieve a single incoming order by code.
    """
    new_item = inbound_orders_service.add_item(order_code, item)
    return CreateInboundOrderItemResponse(data=new_item)


@routes.patch("/{order_code}/state", response={200: GetInboundOrderResponse}, auth=None)
def transition_inbound_order(
    request: HttpRequest, order_code: str, body: InboundOrderTransitionSchema
):
    """
    Transition an inbound order.
    """
    new_item = inbound_orders_service.transition_order(order_code, body.state)
    return GetInboundOrderResponse(data=new_item)


@routes.delete(
    "/{order_code}/items/{product_code}", response={200: EmptyResponse}, auth=None
)
def remove_items_from_inbound_order(
    request: HttpRequest, order_code: str, product_code: str
):
    """
    Retrieve a single incoming order by code.
    """
    result = inbound_orders_service.remove_item(order_code, product_code)
    return EmptyResponse(success=result)
