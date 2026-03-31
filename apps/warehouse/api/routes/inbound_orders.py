from typing import cast

from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import IncomingOrdersPagination
from apps.warehouse.core.schemas.audit import GetAuditTimelineResponse
from apps.warehouse.core.schemas.base import EmptyResponse
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.orders import (
    InboundOrderSchema,
    InboundOrderItemCreateSchema,
    CreateInboundOrderItemResponse,
    InboundOrderCreateOrUpdateSchema,
    GetInboundOrderResponse,
    InboundOrderTransitionSchema,
)
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.orders import inbound_orders_service
from apps.warehouse.core.transformation import inbound_order_orm_to_schema
from apps.warehouse.models.orders import InboundOrder

routes = Router(tags=["inbound_order"])


@routes.get("", response={200: list[InboundOrderSchema]})
@paginate(IncomingOrdersPagination)
def get_inbound_orders(
    request: HttpRequest,
    search_term: str | None = None,
    stock_product_code: str | None = None,
):
    """
    List incoming orders, optionally filtered by code or supplier name.
    """
    qs = cast(
        QuerySet[InboundOrder],
        inbound_orders_service.get_inbound_orders(
            search_term=search_term,
            stock_product_code=stock_product_code,
        ),
    )
    return qs.all()


@routes.post("", response={200: GetInboundOrderResponse})
def create_inbound_order(
    request: HttpRequest, params: InboundOrderCreateOrUpdateSchema
):
    """
    Create an order
    """
    new_order = inbound_orders_service.update_or_create_incoming(
        params,
        context=RequestContext.from_django_request(request),
    )
    return GetInboundOrderResponse(data=new_order)


@routes.get("/{order_code}", response={200: GetInboundOrderResponse})
def get_inbound_order(request: HttpRequest, order_code: str):
    """
    Retrieve a single incoming order by code.
    """
    return GetInboundOrderResponse(
        data=inbound_order_orm_to_schema(InboundOrder.objects.get(code=order_code))
    )


@routes.get("/{order_code}/audits", response={200: GetAuditTimelineResponse})
def get_inbound_order_audits(request: HttpRequest, order_code: str):
    order = InboundOrder.objects.get(code=order_code)
    return GetAuditTimelineResponse(data=audit_service.get_timeline_for_object(order))


@routes.put("/{order_code}", response={200: GetInboundOrderResponse})
def update_inbound_order(
    request: HttpRequest, order_code: str, params: InboundOrderCreateOrUpdateSchema
):
    """
    Update an order
    """
    updated_order = inbound_orders_service.update_or_create_incoming(
        params, context=RequestContext.from_django_request(request), code=order_code
    )
    return GetInboundOrderResponse(data=updated_order)


@routes.get("/{order_code}/pdf")
def get_inbound_order_pdf(request: HttpRequest, order_code: str):
    response = HttpResponse(
        inbound_orders_service.get_pdf(order_code), content_type="application/pdf"
    )
    response["Content-Disposition"] = 'attachment; filename="document.pdf"'
    return response


@routes.get("/{order_code}/html")
def get_inbound_order_html(request: HttpRequest, order_code: str):
    response = HttpResponse(
        inbound_orders_service.get_html(order_code), content_type="text/html"
    )
    # response['Content-Disposition'] = 'attachment; filename="document.pdf"'
    return response


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


@routes.put(
    "/{order_code}/items", response={200: CreateInboundOrderItemResponse}, auth=None
)
def update_item_in_inbound_order(
    request: HttpRequest, order_code: str, item: InboundOrderItemCreateSchema
):
    """
    Update an existing item in incoming order by stock product code.
    """
    updated_item = inbound_orders_service.update_item(order_code, item)
    return CreateInboundOrderItemResponse(data=updated_item)


@routes.patch("/{order_code}/state", response={200: GetInboundOrderResponse})
def transition_inbound_order(
    request: HttpRequest, order_code: str, body: InboundOrderTransitionSchema
):
    """
    Transition an inbound order.
    """
    new_item = inbound_orders_service.transition_order(
        order_code, body.state, context=RequestContext.from_django_request(request)
    )
    return GetInboundOrderResponse(data=new_item)


@routes.delete("/{order_code}/items/{product_code}", response={200: EmptyResponse})
def remove_items_from_inbound_order(
    request: HttpRequest, order_code: str, product_code: str
):
    """
    Retrieve a single incoming order by code.
    """
    result = inbound_orders_service.remove_item(order_code, product_code)
    return EmptyResponse(success=result)
