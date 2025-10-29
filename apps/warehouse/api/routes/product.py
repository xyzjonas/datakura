from __future__ import annotations

from typing import cast

from django.db.models import Q, QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import StockProductPagination
from apps.warehouse.api.schemas.product import (
    GetProductResponse,
    ProductSchema,
    ConversionFactorSchema,
)
from apps.warehouse.api.schemas.warehouse import (
    GetProductWarehouseInfoResponse,
    WarehouseExpandedSchema,
    WarehouseLocationDetailSchema,
    StockItemSchema,
    WarehouseItemSchema,
)
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import WarehouseItem

routes = Router(tags=["product"])


@routes.get("", response={200: list[ProductSchema]}, auth=None)
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
    product = StockProduct.objects.prefetch_related(
        "base_uom", "type", "conversion_factors", "conversion_factors__uom", "group"
    ).get(code=product_code)
    return GetProductResponse(
        data=ProductSchema(
            name=product.name,
            code=product.code,
            type=product.type.name,
            unit=product.base_uom.name,
            group=product.group.name if product.group else None,
            conversion_factors=[
                ConversionFactorSchema(
                    factor=float(cf.conversion_factor),
                    unit_of_measure=cf.uom.name,
                )
                for cf in product.conversion_factors.all()
            ],
            created=product.created,
            changed=product.changed,
        )
    )


@routes.get(
    "/{product_code}/warehouse-info",
    response={200: GetProductWarehouseInfoResponse},
    auth=None,
)
def get_product_warehouse_info(request: HttpRequest, product_code: str):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    # product = StockProduct.objects.prefetch_related(
    #     "base_uom", "type", "conversion_factors", "conversion_factors__uom", "group"
    # ).get(code=product_code)
    items = (
        WarehouseItem.objects.filter(stock_item__code=product_code)
        .prefetch_related(
            "stock_item",
            "uom_at_receipt",
            "warehouse_location",
            "warehouse_location__warehouse",
        )
        .all()
    )

    warehouses: list[WarehouseExpandedSchema] = []
    warehouse_names = set()
    location_names = set()

    for item in items:
        warehouse_model = item.warehouse_location.warehouse
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

        location_model = item.warehouse_location
        if location_model.code not in location_names:
            location = WarehouseLocationDetailSchema(
                code=location_model.code,
                created=location_model.created,
                changed=location_model.changed,
                items=[],
            )
            warehouse.locations.append(location)
            location_names.add(location.code)
        else:
            location = [
                loc for loc in warehouse.locations if loc.code == location_model.code
            ][0]

        location.items.append(
            WarehouseItemSchema(
                code=item.code,
                stock_item=StockItemSchema(
                    code=item.stock_item.code,
                    name=item.stock_item.name,
                    created=item.stock_item.created,
                    changed=item.stock_item.changed,
                ),
                unit_of_measure=item.uom_at_receipt.name,
                factor_at_receipt=float(item.conversion_factor_at_receipt),
                created=item.created,
                changed=item.changed,
                remaining=float(item.remaining),
            )
        )

    return GetProductWarehouseInfoResponse(data=warehouses)
