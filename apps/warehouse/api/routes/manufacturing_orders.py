from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import ManufacturingOrdersPagination
from apps.warehouse.core.schemas.audit import GetAuditTimelineResponse
from apps.warehouse.core.schemas.base import EmptyResponse
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.manufacturing import (
    CreateManufacturingOrderItemResponse,
    GetManufacturingOrderResponse,
    ManufacturingOrderCreateOrUpdateSchema,
    ManufacturingOrderItemCreateSchema,
    ManufacturingOrderSchema,
    ManufacturingOrderTransitionSchema,
)
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.manufacturing import manufacturing_orders_service
from apps.warehouse.core.transformation import manufacturing_order_orm_to_schema
from apps.warehouse.models.manufacturing import ManufacturingOrder

routes = Router(tags=["manufacturing_order"])


@routes.get("", response={200: list[ManufacturingOrderSchema]})
@paginate(ManufacturingOrdersPagination)
def get_manufacturing_orders(
    request: HttpRequest,
    search_term: str | None = None,
    state: str | None = None,
):
    return manufacturing_orders_service.get_manufacturing_orders(
        search_term=search_term,
        state=state,
    )


@routes.post("", response={200: GetManufacturingOrderResponse})
def create_manufacturing_order(
    request: HttpRequest,
    params: ManufacturingOrderCreateOrUpdateSchema,
):
    order = manufacturing_orders_service.create_or_update(
        params,
        context=RequestContext.from_django_request(request),
    )
    return GetManufacturingOrderResponse(data=order)


@routes.get("/{order_code}", response={200: GetManufacturingOrderResponse})
def get_manufacturing_order(request: HttpRequest, order_code: str):
    return GetManufacturingOrderResponse(
        data=manufacturing_order_orm_to_schema(
            ManufacturingOrder.objects.get(code=order_code)
        )
    )


@routes.put("/{order_code}", response={200: GetManufacturingOrderResponse})
def update_manufacturing_order(
    request: HttpRequest,
    order_code: str,
    params: ManufacturingOrderCreateOrUpdateSchema,
):
    order = manufacturing_orders_service.create_or_update(
        params,
        context=RequestContext.from_django_request(request),
        code=order_code,
    )
    return GetManufacturingOrderResponse(data=order)


@routes.post("/{order_code}/transition", response={200: GetManufacturingOrderResponse})
def transition_manufacturing_order(
    request: HttpRequest,
    order_code: str,
    body: ManufacturingOrderTransitionSchema,
):
    order = manufacturing_orders_service.transition_order(
        order_code,
        context=RequestContext.from_django_request(request),
        action=body.action,
    )
    return GetManufacturingOrderResponse(data=order)


@routes.post(
    "/{order_code}/items", response={200: CreateManufacturingOrderItemResponse}
)
def add_item_to_manufacturing_order(
    request: HttpRequest,
    order_code: str,
    item: ManufacturingOrderItemCreateSchema,
):
    new_item = manufacturing_orders_service.add_item(
        order_code,
        item,
        context=RequestContext.from_django_request(request),
    )
    return CreateManufacturingOrderItemResponse(data=new_item)


@routes.put(
    "/{order_code}/items/{item_id}",
    response={200: CreateManufacturingOrderItemResponse},
)
def update_item_in_manufacturing_order(
    request: HttpRequest,
    order_code: str,
    item_id: int,
    item: ManufacturingOrderItemCreateSchema,
):
    updated_item = manufacturing_orders_service.update_item(
        order_code,
        item_id,
        item,
        context=RequestContext.from_django_request(request),
    )
    return CreateManufacturingOrderItemResponse(data=updated_item)


@routes.delete("/{order_code}/items/{item_id}", response={200: EmptyResponse})
def remove_item_from_manufacturing_order(
    request: HttpRequest,
    order_code: str,
    item_id: int,
):
    result = manufacturing_orders_service.remove_item(
        order_code,
        item_id,
        context=RequestContext.from_django_request(request),
    )
    return EmptyResponse(success=result)


@routes.get("/{order_code}/audits", response={200: GetAuditTimelineResponse})
def get_manufacturing_order_audits(request: HttpRequest, order_code: str):
    order = ManufacturingOrder.objects.get(code=order_code)
    return GetAuditTimelineResponse(data=audit_service.get_timeline_for_object(order))
