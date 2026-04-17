from typing import cast

from django.db.models import QuerySet, Q
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import (
    IncomingWarehouseOrdersPagination,
    OutgoingWarehouseOrdersPagination,
    WarehouseLocationsPagination,
)
from apps.warehouse.core.schemas.audit import GetAuditTimelineResponse
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.warehouse import (
    AssignOutboundWarehouseOrderItemRequest,
    GetWarehouseLocationResponse,
    GetWarehouseItemResponse,
    GetWarehouseOrderResponse,
    GetOutboundWarehouseOrderItemCandidatesResponse,
    GetOutboundWarehouseOrderResponse,
    WarehouseOrderCreateSchema,
    InboundWarehouseOrderSchema,
    OutboundWarehouseOrderSchema,
    UpdateWarehouseOrderDraftItemsRequest,
    InboundWarehouseOrderUpdateSchema,
    SetupTrackingWarehouseItemRequest,
    RemoveItemToCreditNoteRequest,
    InboundWarehouseOrderSetStateSchema,
    WarehouseLocationSchema,
    PutawayItemRequest,
    GetWarehousesWithCountsResponse,
    WarehouseWithCountsSchema,
    OffloadItemsToChildOrderRequest,
)
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.core.transformation import (
    location_orm_to_detail_schema,
    location_orm_to_schema_with_count,
)
from apps.warehouse.models.orders import InboundOrderState, OutboundOrderState
from apps.warehouse.models.warehouse import (
    Warehouse,
    WarehouseLocation,
    InboundWarehouseOrder,
    OutboundWarehouseOrder,
)

routes = Router(tags=["warehouse"])


@routes.get("warehouses", response={200: GetWarehousesWithCountsResponse})
def get_warehouses(request: HttpRequest):
    warehouses = Warehouse.objects.prefetch_related("locations").all()
    return GetWarehousesWithCountsResponse(
        data=[
            WarehouseWithCountsSchema(
                name=warehouse.name,
                description=warehouse.description,
                created=warehouse.created,
                changed=warehouse.changed,
                locations=[
                    location_orm_to_schema_with_count(location)
                    for location in warehouse.locations.all()
                ],
            )
            for warehouse in warehouses
        ]
    )


@routes.get(
    "locations",
    response={200: list[WarehouseLocationSchema]},
)
@paginate(WarehouseLocationsPagination)
def get_warehouse_locations(
    request: HttpRequest,
    search_term: str | None = None,
    stock_product_code: str | None = None,
):
    qs = cast(
        QuerySet[WarehouseLocation],
        WarehouseLocation.objects.select_related("warehouse").all(),
    )
    if search_term:
        search_term = search_term.lower()
        qs = qs.filter(Q(code__iexact=search_term) | Q(code__icontains=search_term))
    if stock_product_code:
        qs = qs.filter(items__stock_product__code=stock_product_code).distinct()
    return qs.all()


@routes.get(
    "locations/{warehouse_location_code}",
    response={200: GetWarehouseLocationResponse},
)
def get_warehouse_location(request: HttpRequest, warehouse_location_code: str):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    location = WarehouseLocation.objects.prefetch_related(
        "items",
        "items__stock_product",
        "items__stock_product__unit_of_measure",
        "items__package_type",
        "items__package_type__unit_of_measure",
        # "items__order_in",
    ).get(code=warehouse_location_code)
    return GetWarehouseLocationResponse(data=location_orm_to_detail_schema(location))


@routes.get(
    "items/{item_id}",
    response={200: GetWarehouseItemResponse},
)
def get_warehouse_item(request: HttpRequest, item_id: int):
    item = warehouse_service.get_warehouse_item_detail(item_id)
    return GetWarehouseItemResponse(data=item)


@routes.post(
    "orders-incoming",
    response={200: GetWarehouseOrderResponse},
)
def create_inbound_warehouse_order(
    request: HttpRequest, body: WarehouseOrderCreateSchema
):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    warehouse_order = warehouse_service.create_inbound_order(
        body, context=RequestContext.from_django_request(request)
    )
    return GetWarehouseOrderResponse(data=warehouse_order)


@routes.get(
    "orders-incoming",
    response={200: list[InboundWarehouseOrderSchema]},
)
@paginate(IncomingWarehouseOrdersPagination)
def get_inbound_warehouse_orders(request: HttpRequest, search_term: str | None = None):
    qs = cast(
        QuerySet[InboundWarehouseOrder],
        InboundWarehouseOrder.objects.select_related("order")
        .prefetch_related(
            "order_items",
            "order_items__stock_product",
            "order_items__stock_product__unit_of_measure",
            "order_items__package_type",
            "items",
            "order__items",
            "warehouse_movements",
            "warehouse_movements__location_from",
            "warehouse_movements__location_to",
            "warehouse_movements__stock_product",
            "warehouse_movements__item",
        )
        .exclude(order__state=InboundOrderState.CANCELLED)
        .exclude(order__state=InboundOrderState.COMPLETED),
    )
    if search_term:
        search_term = search_term.lower()
        qs = qs.filter(
            Q(code__iexact=search_term)
            | Q(code__icontains=search_term)
            | Q(order__code__icontains=search_term)
        )
    return qs.all()


@routes.get(
    "orders-outgoing",
    response={200: list[OutboundWarehouseOrderSchema]},
)
@paginate(OutgoingWarehouseOrdersPagination)
def get_outbound_warehouse_orders(request: HttpRequest, search_term: str | None = None):
    qs = cast(
        QuerySet[OutboundWarehouseOrder],
        OutboundWarehouseOrder.objects.select_related("order", "order__customer")
        .prefetch_related(
            "order__items",
            "warehouse_movements",
            "warehouse_movements__location_from",
            "warehouse_movements__location_to",
            "warehouse_movements__stock_product",
            "warehouse_movements__item",
        )
        .exclude(order__state=OutboundOrderState.CANCELLED)
        .exclude(order__state=OutboundOrderState.COMPLETED),
    )
    if search_term:
        search_term = search_term.lower()
        qs = qs.filter(
            Q(code__iexact=search_term)
            | Q(code__icontains=search_term)
            | Q(order__code__icontains=search_term)
        )
    return qs.all()


@routes.get(
    "orders-incoming/{code}",
    response={200: GetWarehouseOrderResponse},
)
def get_inbound_warehouse_order(request: HttpRequest, code: str):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    order = warehouse_service.get_inbound_warehouse_order(code)
    return GetWarehouseOrderResponse(data=order)


@routes.get(
    "orders-outgoing/{code}",
    response={200: GetOutboundWarehouseOrderResponse},
)
def get_outbound_warehouse_order(request: HttpRequest, code: str):
    order = warehouse_service.get_outbound_warehouse_order(code)
    return GetOutboundWarehouseOrderResponse(data=order)


@routes.get(
    "orders-outgoing/{code}/order-items/{item_id}/candidates",
    response={200: GetOutboundWarehouseOrderItemCandidatesResponse},
)
def get_outbound_warehouse_order_item_candidates(
    request: HttpRequest,
    code: str,
    item_id: int,
):
    return GetOutboundWarehouseOrderItemCandidatesResponse(
        data=warehouse_service.get_outbound_item_candidates(code, item_id)
    )


@routes.post(
    "orders-outgoing/{code}/order-items/{item_id}/assign",
    response={200: GetOutboundWarehouseOrderResponse},
)
def assign_outbound_warehouse_order_item(
    request: HttpRequest,
    code: str,
    item_id: int,
    body: AssignOutboundWarehouseOrderItemRequest,
):
    order = warehouse_service.assign_outbound_item(
        warehouse_order_code=code,
        order_item_id=item_id,
        warehouse_item_id=body.warehouse_item_id,
        context=RequestContext.from_django_request(request),
    )
    return GetOutboundWarehouseOrderResponse(data=order)


@routes.get(
    "orders-incoming/{code}/audits",
    response={200: GetAuditTimelineResponse},
)
def get_inbound_warehouse_order_audits(request: HttpRequest, code: str):
    order = InboundWarehouseOrder.objects.get(code=code)
    return GetAuditTimelineResponse(data=audit_service.get_timeline_for_object(order))


@routes.put(
    "orders-incoming/{code}",
    response={200: GetWarehouseOrderResponse},
)
def update_inbound_warehouse_order(
    request: HttpRequest, code: str, body: InboundWarehouseOrderUpdateSchema
):
    warehouse_service.update_inbound_order(
        code, body, context=RequestContext.from_django_request(request)
    )
    return GetWarehouseOrderResponse(
        data=warehouse_service.get_inbound_warehouse_order(code)
    )


@routes.post(
    "orders-incoming/{code}/order-items",
    response={200: GetWarehouseOrderResponse},
)
def update_inbound_warehouse_order_items(
    request: HttpRequest, code: str, body: UpdateWarehouseOrderDraftItemsRequest
):
    order = warehouse_service.add_or_remove_inbound_order_items(
        code,
        body.to_be_removed,
        body.to_be_added,
        context=RequestContext.from_django_request(request),
    )
    return GetWarehouseOrderResponse(data=order)


@routes.post(
    "orders-incoming/{code}/order-items/{item_id}/track",
    response={200: GetWarehouseOrderResponse},
)
def track_inbound_warehouse_order_item(
    request: HttpRequest,
    code: str,
    item_id: int,
    body: SetupTrackingWarehouseItemRequest,
):
    order = warehouse_service.setup_tracking_for_inbound_order_item(
        code,
        item_id,
        body.to_be_added,
        context=RequestContext.from_django_request(request),
    )
    return GetWarehouseOrderResponse(data=order)


@routes.delete(
    "orders-incoming/{code}/order-items/{item_id}",
    response={200: GetWarehouseOrderResponse},
)
def dissolve_inbound_warehouse_order_item(
    request: HttpRequest, code: str, item_id: int
):
    order = warehouse_service.dissolve_inbound_order_item(code, item_id)
    return GetWarehouseOrderResponse(data=order)


@routes.post(
    "orders-incoming/{code}/credit",
    response={200: GetWarehouseOrderResponse},
)
def remove_from_order_to_credit_note(
    request: HttpRequest, code: str, body: RemoveItemToCreditNoteRequest
):
    order = warehouse_service.remove_from_order_to_credit_note(
        code,
        body.item_id,
        body.amount,
        context=RequestContext.from_django_request(request),
    )
    return GetWarehouseOrderResponse(data=order)


@routes.post(
    "orders-incoming/{code}/transition",
    response={200: GetWarehouseOrderResponse},
)
def transition_inbound_warehouse_order(
    request: HttpRequest, code: str, body: InboundWarehouseOrderSetStateSchema
):
    warehouse_service.transition_inbound_order(
        code,
        context=RequestContext.from_django_request(request),
        location_code=body.location_code,
    )

    return GetWarehouseOrderResponse(
        data=warehouse_service.get_inbound_warehouse_order(code)
    )


@routes.post(
    "orders-incoming/{code}/items/{item_id}/putaway",
    response={200: GetWarehouseOrderResponse},
)
def putaway_inbound_warehouse_order_item(
    request: HttpRequest,
    code: str,
    item_id: int,
    body: PutawayItemRequest,
):
    warehouse_service.putaway_item(
        item_id=item_id,
        warehouse_order_code=code,
        new_location_code=body.new_location_code,
        context=RequestContext.from_django_request(request),
    )
    order = warehouse_service.get_inbound_warehouse_order(code)
    return GetWarehouseOrderResponse(data=order)


@routes.post(
    "orders-incoming/{code}/offload",
    response={200: GetWarehouseOrderResponse},
)
def offload_items_to_child_order(
    request: HttpRequest,
    code: str,
    body: OffloadItemsToChildOrderRequest,
):
    from decimal import Decimal

    items = [(item.item_id, Decimal(str(item.amount))) for item in body.items]
    order = warehouse_service.offload_items_to_child_order(
        parent_code=code,
        items=items,
        context=RequestContext.from_django_request(request),
    )
    return GetWarehouseOrderResponse(data=order)


@routes.post(
    "orders-outgoing/{code}/offload",
    response={200: GetOutboundWarehouseOrderResponse},
)
def offload_outbound_items_to_child_order(
    request: HttpRequest,
    code: str,
    body: OffloadItemsToChildOrderRequest,
):
    from decimal import Decimal

    items = [(item.item_id, Decimal(str(item.amount))) for item in body.items]
    order = warehouse_service.offload_outbound_items_to_child_order(
        parent_code=code,
        items=items,
        context=RequestContext.from_django_request(request),
    )
    return GetOutboundWarehouseOrderResponse(data=order)
