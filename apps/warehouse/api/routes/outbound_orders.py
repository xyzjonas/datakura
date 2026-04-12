from typing import cast

from django.core.files.uploadedfile import UploadedFile as DjangoUploadedFile
from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import File, Form, Router
from ninja.files import UploadedFile
from ninja.pagination import paginate

from apps.warehouse.api.pagination import OutgoingOrdersPagination
from apps.warehouse.core.schemas.audit import GetAuditTimelineResponse
from apps.warehouse.core.schemas.base import EmptyResponse
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.invoice import InvoiceStoreSchema
from apps.warehouse.core.schemas.orders import (
    CreateOutboundOrderItemResponse,
    GetOutboundOrderResponse,
    OutboundOrderCreateOrUpdateSchema,
    OutboundOrderItemCreateSchema,
    OutboundOrderSchema,
    OutboundOrderTransitionSchema,
)
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.outbound_orders import outbound_orders_service
from apps.warehouse.models.orders import OutboundOrder

routes = Router(tags=["outbound_order"])


@routes.get("", response={200: list[OutboundOrderSchema]})
@paginate(OutgoingOrdersPagination)
def get_outbound_orders(
    request: HttpRequest,
    search_term: str | None = None,
    stock_product_code: str | None = None,
):
    qs = cast(
        QuerySet[OutboundOrder],
        outbound_orders_service.get_outbound_orders(
            search_term=search_term,
            stock_product_code=stock_product_code,
        ),
    )
    return qs.all()


@routes.post("", response={200: GetOutboundOrderResponse})
def create_outbound_order(
    request: HttpRequest, params: OutboundOrderCreateOrUpdateSchema
):
    new_order = outbound_orders_service.update_or_create_outgoing(
        params,
        context=RequestContext.from_django_request(request),
    )
    return GetOutboundOrderResponse(data=new_order)


@routes.get("/{order_code}", response={200: GetOutboundOrderResponse})
def get_outbound_order(request: HttpRequest, order_code: str):
    return GetOutboundOrderResponse(
        data=outbound_orders_service.get_outbound_order(order_code)
    )


@routes.get("/{order_code}/audits", response={200: GetAuditTimelineResponse})
def get_outbound_order_audits(request: HttpRequest, order_code: str):
    order = OutboundOrder.objects.get(code=order_code)
    return GetAuditTimelineResponse(data=audit_service.get_timeline_for_object(order))


@routes.put("/{order_code}", response={200: GetOutboundOrderResponse})
def update_outbound_order(
    request: HttpRequest, order_code: str, params: OutboundOrderCreateOrUpdateSchema
):
    updated_order = outbound_orders_service.update_or_create_outgoing(
        params, context=RequestContext.from_django_request(request), code=order_code
    )
    return GetOutboundOrderResponse(data=updated_order)


@routes.post("/{order_code}/invoice", response={200: GetOutboundOrderResponse})
def store_outbound_order_invoice(
    request: HttpRequest,
    order_code: str,
    body: Form[InvoiceStoreSchema],
    invoice_file: File[UploadedFile] | None = None,
):
    resolved_invoice_file = invoice_file or cast(
        DjangoUploadedFile | None, request.FILES.get("invoice_file")
    )

    updated_order = outbound_orders_service.store_invoice(
        order_code,
        body,
        context=RequestContext.from_django_request(request),
        invoice_file=resolved_invoice_file,
    )
    return GetOutboundOrderResponse(data=updated_order)


@routes.post(
    "/{order_code}/items", response={200: CreateOutboundOrderItemResponse}, auth=None
)
def add_item_to_outbound_order(
    request: HttpRequest, order_code: str, item: OutboundOrderItemCreateSchema
):
    new_item = outbound_orders_service.add_item(order_code, item)
    return CreateOutboundOrderItemResponse(data=new_item)


@routes.put(
    "/{order_code}/items", response={200: CreateOutboundOrderItemResponse}, auth=None
)
def update_item_in_outbound_order(
    request: HttpRequest, order_code: str, item: OutboundOrderItemCreateSchema
):
    updated_item = outbound_orders_service.update_item(order_code, item)
    return CreateOutboundOrderItemResponse(data=updated_item)


@routes.post("/{order_code}/transition", response={200: GetOutboundOrderResponse})
def transition_outbound_order(
    request: HttpRequest, order_code: str, body: OutboundOrderTransitionSchema
):
    new_item = outbound_orders_service.transition_order(
        order_code,
        context=RequestContext.from_django_request(request),
        action=body.action,
    )
    return GetOutboundOrderResponse(data=new_item)


@routes.delete("/{order_code}/items/{product_code}", response={200: EmptyResponse})
def remove_items_from_outbound_order(
    request: HttpRequest, order_code: str, product_code: str
):
    result = outbound_orders_service.remove_item(order_code, product_code)
    return EmptyResponse(success=result)
