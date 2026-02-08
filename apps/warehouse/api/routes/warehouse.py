from typing import cast

from django.db.models import QuerySet, Q
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import IncomingWarehouseOrdersPagination
from apps.warehouse.core.schemas.warehouse import (
    GetWarehousesResponse,
    WarehouseSchema,
    GetWarehouseLocationResponse,
    GetWarehouseOrderResponse,
    WarehouseOrderCreateSchema,
    InboundWarehouseOrderSchema,
    UpdateWarehouseOrderDraftItemsRequest,
    InboundWarehouseOrderUpdateSchema,
    SetupTrackingWarehouseItemRequest,
    RemoveItemToCreditNoteRequest,
)
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.core.transformation import (
    location_orm_to_schema,
    location_orm_to_detail_schema,
)
from apps.warehouse.models.orders import InboundOrderState
from apps.warehouse.models.warehouse import (
    Warehouse,
    WarehouseLocation,
    InboundWarehouseOrder,
)

routes = Router(tags=["warehouse"])


@routes.get("warehouses", response={200: GetWarehousesResponse}, auth=None)
def get_warehouses(request: HttpRequest):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    warehouses = Warehouse.objects.prefetch_related("locations").all()
    return GetWarehousesResponse(
        data=[
            WarehouseSchema(
                name=warehouse.name,
                description=warehouse.description,
                created=warehouse.created,
                changed=warehouse.changed,
                locations=[
                    location_orm_to_schema(location)
                    for location in warehouse.locations.all()
                ],
            )
            for warehouse in warehouses
        ]
    )


@routes.get(
    "locations/{warehouse_location_code}",
    response={200: GetWarehouseLocationResponse},
    auth=None,
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
        "items__order_in",
    ).get(code=warehouse_location_code)
    return GetWarehouseLocationResponse(data=location_orm_to_detail_schema(location))


@routes.post(
    "orders-incoming",
    response={200: GetWarehouseOrderResponse},
    auth=None,
)
def create_inbound_warehouse_order(
    request: HttpRequest, body: WarehouseOrderCreateSchema
):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    warehouse_order = warehouse_service.create_inbound_order(body)
    return GetWarehouseOrderResponse(data=warehouse_order)


@routes.get(
    "orders-incoming",
    response={200: list[InboundWarehouseOrderSchema]},
    auth=None,
)
@paginate(IncomingWarehouseOrdersPagination)
def get_inbound_warehouse_orders(request: HttpRequest, search_term: str | None = None):
    qs = cast(
        QuerySet[InboundWarehouseOrder],
        InboundWarehouseOrder.objects.select_related("order")
        .prefetch_related("items")
        .exclude(order__state=InboundOrderState.CANCELLED),
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
    auth=None,
)
def get_inbound_warehouse_order(request: HttpRequest, code: str):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    order = warehouse_service.get_inbound_warehouse_order(code)
    return GetWarehouseOrderResponse(data=order)


@routes.put(
    "orders-incoming/{code}",
    response={200: GetWarehouseOrderResponse},
    auth=None,
)
def update_inbound_warehouse_order(
    request: HttpRequest, code: str, body: InboundWarehouseOrderUpdateSchema
):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    return GetWarehouseOrderResponse(
        data=warehouse_service.update_inbound_order(code, body)
    )


@routes.post(
    "orders-incoming/{code}/items",
    response={200: GetWarehouseOrderResponse},
    auth=None,
)
def update_inbound_warehouse_order_items(
    request: HttpRequest, code: str, body: UpdateWarehouseOrderDraftItemsRequest
):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    order = warehouse_service.add_or_remove_inbound_order_items(
        code, body.to_be_removed, body.to_be_added
    )
    return GetWarehouseOrderResponse(data=order)


@routes.post(
    "orders-incoming/{code}/items/{item_code}",
    response={200: GetWarehouseOrderResponse},
    auth=None,
)
def track_inbound_warehouse_order_item(
    request: HttpRequest,
    code: str,
    item_code: str,
    body: SetupTrackingWarehouseItemRequest,
):
    order = warehouse_service.setup_tracking_for_inbound_order_item(
        code, item_code, body.to_be_added
    )
    return GetWarehouseOrderResponse(data=order)


@routes.delete(
    "orders-incoming/{code}/items/{item_code}",
    response={200: GetWarehouseOrderResponse},
    auth=None,
)
def dissolve_inbound_warehouse_order_item(
    request: HttpRequest, code: str, item_code: str
):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    order = warehouse_service.dissolve_inbound_order_item(code, item_code)
    return GetWarehouseOrderResponse(data=order)


@routes.post(
    "orders-incoming/{code}/credit",
    response={200: GetWarehouseOrderResponse},
    auth=None,
)
def remove_from_order_to_credit_note(
    request: HttpRequest, code: str, body: RemoveItemToCreditNoteRequest
):
    order = warehouse_service.remove_from_order_to_credit_note(
        code, body.item_code, body.amount
    )
    return GetWarehouseOrderResponse(data=order)


# @routes.post(
#     "orders-incoming/{code}/items",
#     response={200: GetWarehouseOrderResponse},
#     auth=None,
# )
# def update_inbound_warehouse_order_items(
#     request: HttpRequest, code: str, body: UpdateWarehouseOrderDraftItemsRequest
# ):
#     # user = authenticate(
#     #     request, username=credentials.username, password=credentials.password
#     # )
#     order = warehouse_service.add_or_remove_inbound_order_items(
#         code, body.to_be_removed, body.to_be_added
#     )
#     return GetWarehouseOrderResponse(data=order)
