from __future__ import annotations

from typing import cast

from django.db.models import Q, QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import ProductTypePagination, StockProductPagination
from apps.warehouse.core.schemas.audit import GetAuditTimelineResponse
from apps.warehouse.core.schemas.type import (
    GetProductTypeResponse,
    ProductTypeCreateOrUpdateSchema,
    ProductTypeSchema,
)
from apps.warehouse.core.schemas.product import (
    GetProductResponse,
    ProductSchema,
    ProductCreateOrUpdateSchema,
    ProductDuplicateSchema,
    ProductBarcodeCreateSchema,
    DynamicProductPriceCreateSchema,
    DynamicProductPriceUpdateSchema,
)
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.schemas.warehouse import (
    GetProductWarehouseInfoResponse,
    WarehouseExpandedSchema,
    GetProductWarehouseAvailabilityResponse,
    WarehouseLocationDetailSchema,
)
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.core.services.products import stock_product_service
from apps.warehouse.core.transformation import (
    get_product_by_code,
    product_type_orm_to_schema,
    warehouse_item_orm_to_schema,
    location_orm_to_schema,
)
from apps.warehouse.models.product import ProductType, StockProduct
from apps.warehouse.models.warehouse import WarehouseItem, InboundWarehouseOrderState

routes = Router(tags=["product"])


@routes.get("/types", response={200: list[ProductTypeSchema]})
@paginate(ProductTypePagination)
def get_types(request: HttpRequest, search_term: str | None = None):
    qs = cast(QuerySet[ProductType], ProductType.objects.all())
    if search_term:
        search_term = search_term.lower()
        qs = qs.filter(name__icontains=search_term)

    return qs.all()


@routes.post("/types", response={200: GetProductTypeResponse})
def create_type(request: HttpRequest, body: ProductTypeCreateOrUpdateSchema):
    product_type, _ = ProductType.objects.get_or_create(name=body.name)
    return GetProductTypeResponse(data=product_type_orm_to_schema(product_type))


@routes.put("/types/{type_name}", response={200: GetProductTypeResponse})
def update_type(
    request: HttpRequest,
    type_name: str,
    body: ProductTypeCreateOrUpdateSchema,
):
    product_type = ProductType.objects.get(name=type_name)
    product_type.name = body.name
    product_type.save()
    return GetProductTypeResponse(data=product_type_orm_to_schema(product_type))


@routes.get("", response={200: list[ProductSchema]})
@paginate(StockProductPagination)
def get_products(
    request: HttpRequest,
    search_term: str | None = None,
    product_type: str | None = None,
    product_group: str | None = None,
):
    qs = cast(
        QuerySet[StockProduct],
        StockProduct.objects.prefetch_related(
            "dynamic_prices__group",
            "dynamic_prices__customer",
        ),
    )
    if search_term:
        search_term = search_term.lower()
        qs = qs.filter(
            Q(code__iexact=search_term)
            | Q(code__icontains=search_term)
            | Q(name__icontains=search_term)
        )

    if product_type:
        qs = qs.filter(type__name=product_type)

    if product_group:
        qs = qs.filter(group__name=product_group)

    return qs.all()


@routes.post("", response={200: GetProductResponse})
def create_product(request: HttpRequest, body: ProductCreateOrUpdateSchema):
    return GetProductResponse(data=stock_product_service.create_product(body))


@routes.get("/{product_code}", response={200: GetProductResponse})
def get_product(request: HttpRequest, product_code: str):
    # user = authenticate(
    #     request, username=credentials.username, password=credentials.password
    # )
    return GetProductResponse(data=get_product_by_code(product_code))


@routes.put("/{product_code}", response={200: GetProductResponse})
def update_product(
    request: HttpRequest,
    product_code: str,
    body: ProductCreateOrUpdateSchema,
):
    return GetProductResponse(
        data=stock_product_service.update_product(product_code, body)
    )


@routes.post("/{product_code}/duplicate", response={200: GetProductResponse})
def duplicate_product(
    request: HttpRequest,
    product_code: str,
    body: ProductDuplicateSchema,
):
    return GetProductResponse(
        data=stock_product_service.duplicate_product(product_code, body)
    )


@routes.get("/{product_code}/audits", response={200: GetAuditTimelineResponse})
def get_product_audits(request: HttpRequest, product_code: str):
    product = StockProduct.objects.get(code=product_code)
    return GetAuditTimelineResponse(data=audit_service.get_timeline_for_object(product))


@routes.post("/{product_code}/barcodes", response={200: GetProductResponse})
def add_product_barcode(
    request: HttpRequest, product_code: str, body: ProductBarcodeCreateSchema
):
    return GetProductResponse(
        data=stock_product_service.add_barcode(product_code, body)
    )


@routes.post("/{product_code}/prices", response={200: GetProductResponse})
def add_product_dynamic_price(
    request: HttpRequest,
    product_code: str,
    body: DynamicProductPriceCreateSchema,
):
    return GetProductResponse(
        data=stock_product_service.add_dynamic_price(product_code, body)
    )


@routes.patch("/{product_code}/prices/{price_id}", response={200: GetProductResponse})
def update_product_dynamic_price(
    request: HttpRequest,
    product_code: str,
    price_id: int,
    body: DynamicProductPriceUpdateSchema,
):
    return GetProductResponse(
        data=stock_product_service.update_dynamic_price(product_code, price_id, body)
    )


@routes.delete("/{product_code}/prices/{price_id}", response={200: GetProductResponse})
def delete_product_dynamic_price(
    request: HttpRequest,
    product_code: str,
    price_id: int,
):
    return GetProductResponse(
        data=stock_product_service.delete_dynamic_price(product_code, price_id)
    )


@routes.get(
    "/{product_code}/warehouse-info",
    response={200: GetProductWarehouseInfoResponse},
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
)
def get_product_warehouse_availability(request: HttpRequest, product_code: str):
    return GetProductWarehouseAvailabilityResponse(
        data=warehouse_service.get_total_availability(product_code)
    )
