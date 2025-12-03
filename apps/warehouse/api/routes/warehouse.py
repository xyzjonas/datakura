from django.http import HttpRequest
from ninja import Router

from apps.warehouse.core.schemas.warehouse import (
    GetWarehousesResponse,
    WarehouseSchema,
    WarehouseLocationSchema,
    GetWarehouseLocationResponse,
    WarehouseLocationDetailSchema,
    GetWarehouseOrderResponse,
)
from apps.warehouse.core.transformation import (
    warehouse_item_orm_to_schema,
    warehouse_inbound_order_orm_to_schema,
)
from apps.warehouse.models.warehouse import (
    Warehouse,
    WarehouseLocation,
    WarehouseOrderIn,
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
                    WarehouseLocationSchema(
                        code=location.code,
                        created=location.created,
                        changed=location.changed,
                    )
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
    ).get(code=warehouse_location_code)
    return GetWarehouseLocationResponse(
        data=WarehouseLocationDetailSchema(
            code=location.code,
            created=location.created,
            changed=location.changed,
            items=[warehouse_item_orm_to_schema(item) for item in location.items.all()],
        )
    )


@routes.get(
    "orders-incoming/{code}",
    response={200: GetWarehouseLocationResponse},
    auth=None,
)
def get_warehouse_order(request: HttpRequest, code: str):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    order = WarehouseOrderIn.objects.prefetch_related(
        "items",
        "items__stock_product",
        "items__stock_product__unit_of_measure",
        "items__package_type",
        "items__package_type__unit_of_measure",
    ).get(code=code)
    return GetWarehouseOrderResponse(data=warehouse_inbound_order_orm_to_schema(order))
