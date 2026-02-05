from __future__ import annotations

from typing import cast

from django.db.models import Q, QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import StockProductPagination
from apps.warehouse.core.schemas.product import (
    GetProductResponse,
    ProductSchema,
)
from apps.warehouse.core.schemas.warehouse import (
    GetProductWarehouseInfoResponse,
    WarehouseExpandedSchema,
    GetProductWarehouseAvailabilityResponse,
    WarehouseLocationDetailSchema,
)
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.core.transformation import (
    get_product_by_code,
    warehouse_item_orm_to_schema,
    location_orm_to_schema,
)
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import WarehouseItem, InboundWarehouseOrderState

routes = Router(tags=["product"])


@routes.get("", response={200: list[ProductSchema]})
@paginate(StockProductPagination)
def get_products(request: HttpRequest, search_term: str | None = None):
    qs = cast(QuerySet[StockProduct], StockProduct.objects)
    if search_term:
        search_term = search_term.lower()
        qs = qs.filter(
            Q(code__iexact=search_term)
            | Q(code__icontains=search_term)
            | Q(name__icontains=search_term)
        )

    return qs.all()


@routes.get("/{product_code}", response={200: GetProductResponse}, auth=None)
def get_product(request: HttpRequest, product_code: str):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    return GetProductResponse(data=get_product_by_code(product_code))


@routes.get(
    "/{product_code}/warehouse-info",
    response={200: GetProductWarehouseInfoResponse},
    auth=None,
)
def get_product_warehouse_info(request: HttpRequest, product_code: str):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    items = (
        WarehouseItem.objects.filter(stock_product__code=product_code)
        .exclude(order_in__state=InboundWarehouseOrderState.DRAFT)
        .prefetch_related(
            "package_type",
            "stock_product",
            "location",
            "location__warehouse",
        )
        .all()
    )

    warehouses: list[WarehouseExpandedSchema] = []
    warehouse_names = set()
    location_names = set()

    for item in items:
        warehouse_model = item.location.warehouse
        if warehouse_model.name not in warehouse_names:
            warehouse = WarehouseExpandedSchema(
                name=warehouse_model.name,
                description=warehouse_model.description,
                created=warehouse_model.created,
                changed=warehouse_model.changed,
                locations=[],
            )
            warehouses.append(warehouse)
            warehouse_names.add(warehouse.name)
        else:
            warehouse = [war for war in warehouses if war.name == warehouse_model.name][
                0
            ]

        location_model = item.location
        if location_model.code not in location_names:
            location = WarehouseLocationDetailSchema(
                **location_orm_to_schema(location_model).model_dump(), items=[]
            )
            warehouse.locations.append(location)
            location_names.add(location.code)
        else:
            location = [
                loc for loc in warehouse.locations if loc.code == location_model.code
            ][0]

        location.items.append(warehouse_item_orm_to_schema(item))

    return GetProductWarehouseInfoResponse(data=warehouses)


@routes.get(
    "/{product_code}/warehouse-availablity",
    response={200: GetProductWarehouseAvailabilityResponse},
    auth=None,
)
def get_product_warehouse_availability(request: HttpRequest, product_code: str):
    return GetProductWarehouseAvailabilityResponse(
        data=warehouse_service.get_total_availability(product_code)
    )
