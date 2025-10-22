from django.http import HttpRequest
from ninja import Router

from apps.warehouse.api.schemas.warehouse import (
    GetWarehousesResponse,
    WarehouseSchema,
    WarehouseLocationSchema,
    WarehouseItemSchema,
    StockItemSchema,
    PackageTypeSchema,
    GetWarehouseLocationResponse,
    WarehouseLocationDetailSchema,
)
from apps.warehouse.models.warehouse import Warehouse, WarehouseLocation

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
    "locations/{warehouse_location_id}",
    response={200: GetWarehouseLocationResponse},
    auth=None,
)
def get_warehouse_location(request: HttpRequest, warehouse_location_code: str):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    location = WarehouseLocation.objects.prefetch_related(
        "items", "items__stock_item", "items__package_type"
    ).get(code=warehouse_location_code)
    return GetWarehouseLocationResponse(
        data=WarehouseLocationDetailSchema(
            code=location.code,
            created=location.created,
            changed=location.changed,
            items=[
                WarehouseItemSchema(
                    stock_item=StockItemSchema(
                        code=item.stock_item.code,
                        name=item.stock_item.name,
                        created=item.stock_item.created,
                        changed=item.stock_item.changed,
                    ),
                    package_type=PackageTypeSchema(
                        name=item.package_type.name,
                        description=item.package_type.description,
                        count=item.package_type.count,
                        created=item.package_type.created,
                        changed=item.package_type.changed,
                    ),
                    created=item.created,
                    changed=item.changed,
                    remaining=item.remaining,
                )
                for item in location.items.all()
            ],
        )
    )
