from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import OutboundCalculationsPagination
from apps.warehouse.core.schemas.audit import GetAuditTimelineResponse
from apps.warehouse.core.schemas.base import EmptyResponse
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.orders import (
    CreateOutboundOrderItemResponse,
    GetOutboundCalculationResponse,
    GetOutboundOrderResponse,
    OutboundCalculationCreateOrUpdateSchema,
    OutboundCalculationSchema,
    OutboundCalculationTransitionSchema,
    OutboundOrderItemCreateSchema,
    ReorderItemSchema,
)
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.outbound_calculations import (
    outbound_calculations_service,
)
from apps.warehouse.models.orders import OutboundCalculation

routes = Router(tags=["outbound_calculation"])


@routes.get("", response={200: list[OutboundCalculationSchema]})
@paginate(OutboundCalculationsPagination)
def get_outbound_calculations(
    request: HttpRequest,
    search_term: str | None = None,
    stock_product_code: str | None = None,
    customer_code: str | None = None,
    include_all: bool = False,
):
    """List calculations (deleted ones never; closed ones only with `include_all`)."""
    return outbound_calculations_service.get_calculations(
        search_term=search_term,
        stock_product_code=stock_product_code,
        customer_code=customer_code,
        include_all=include_all,
    )


@routes.post("", response={200: GetOutboundCalculationResponse})
def create_outbound_calculation(
    request: HttpRequest, params: OutboundCalculationCreateOrUpdateSchema
):
    return GetOutboundCalculationResponse(
        data=outbound_calculations_service.update_or_create(
            params, context=RequestContext.from_django_request(request)
        )
    )


@routes.get("/{calculation_code}", response={200: GetOutboundCalculationResponse})
def get_outbound_calculation(request: HttpRequest, calculation_code: str):
    return GetOutboundCalculationResponse(
        data=outbound_calculations_service.get_calculation(calculation_code)
    )


@routes.put("/{calculation_code}", response={200: GetOutboundCalculationResponse})
def update_outbound_calculation(
    request: HttpRequest,
    calculation_code: str,
    params: OutboundCalculationCreateOrUpdateSchema,
):
    return GetOutboundCalculationResponse(
        data=outbound_calculations_service.update_or_create(
            params,
            context=RequestContext.from_django_request(request),
            code=calculation_code,
        )
    )


@routes.delete("/{calculation_code}", response={200: EmptyResponse})
def delete_outbound_calculation(request: HttpRequest, calculation_code: str):
    """Soft delete: the calculation is only marked as deleted and kept."""
    outbound_calculations_service.delete(
        calculation_code, context=RequestContext.from_django_request(request)
    )
    return EmptyResponse()


@routes.get("/{calculation_code}/audits", response={200: GetAuditTimelineResponse})
def get_outbound_calculation_audits(request: HttpRequest, calculation_code: str):
    calculation = OutboundCalculation.objects.active().get(code=calculation_code)
    return GetAuditTimelineResponse(
        data=audit_service.get_timeline_for_object(calculation)
    )


@routes.post(
    "/{calculation_code}/items", response={200: CreateOutboundOrderItemResponse}
)
def add_item_to_outbound_calculation(
    request: HttpRequest, calculation_code: str, item: OutboundOrderItemCreateSchema
):
    return CreateOutboundOrderItemResponse(
        data=outbound_calculations_service.add_item(calculation_code, item)
    )


@routes.put(
    "/{calculation_code}/items/{item_index}",
    response={200: CreateOutboundOrderItemResponse},
)
def update_item_in_outbound_calculation(
    request: HttpRequest,
    calculation_code: str,
    item_index: int,
    item: OutboundOrderItemCreateSchema,
):
    return CreateOutboundOrderItemResponse(
        data=outbound_calculations_service.update_item(
            calculation_code, item_index, item
        )
    )


@routes.put(
    "/{calculation_code}/items/{item_index}/reorder",
    response={200: GetOutboundCalculationResponse},
)
def reorder_item_in_outbound_calculation(
    request: HttpRequest,
    calculation_code: str,
    item_index: int,
    payload: ReorderItemSchema,
):
    return GetOutboundCalculationResponse(
        data=outbound_calculations_service.reorder_item(
            calculation_code, item_index, payload.new_index
        )
    )


@routes.delete(
    "/{calculation_code}/items/{item_index}",
    response={200: GetOutboundCalculationResponse},
)
def remove_item_from_outbound_calculation(
    request: HttpRequest, calculation_code: str, item_index: int
):
    return GetOutboundCalculationResponse(
        data=outbound_calculations_service.remove_item(calculation_code, item_index)
    )


@routes.post(
    "/{calculation_code}/duplicate", response={200: GetOutboundCalculationResponse}
)
def duplicate_outbound_calculation(request: HttpRequest, calculation_code: str):
    return GetOutboundCalculationResponse(
        data=outbound_calculations_service.duplicate(
            calculation_code, context=RequestContext.from_django_request(request)
        )
    )


@routes.post(
    "/{calculation_code}/transition", response={200: GetOutboundCalculationResponse}
)
def transition_outbound_calculation(
    request: HttpRequest,
    calculation_code: str,
    body: OutboundCalculationTransitionSchema,
):
    return GetOutboundCalculationResponse(
        data=outbound_calculations_service.transition(
            calculation_code,
            context=RequestContext.from_django_request(request),
            action=body.action,
        )
    )


@routes.post(
    "/{calculation_code}/create-order", response={200: GetOutboundOrderResponse}
)
def create_order_from_outbound_calculation(request: HttpRequest, calculation_code: str):
    """Flip the calculation over to an order (1:1 copy, state `submitted`)."""
    return GetOutboundOrderResponse(
        data=outbound_calculations_service.create_order(
            calculation_code, context=RequestContext.from_django_request(request)
        )
    )
