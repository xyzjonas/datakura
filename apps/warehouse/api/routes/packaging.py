from __future__ import annotations

from typing import cast

from django.db.models import Q, QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import UnitOfMeasurePagination
from apps.warehouse.core.schemas.packaging import (
    DeletePackageTypeResponse,
    GetPackageTypeResponse,
    GetPackageTypesResponse,
    GetUnitOfMeasureResponse,
    PackageTypeCreateOrUpdateSchema,
    PutInPackageRequestSchema,
    PutInPackageResponse,
    PutInBatchRequestSchema,
    PutInSerialRequestSchema,
    UnitOfMeasureSchema,
    UnitOfMeasureCreateOrUpdateSchema,
)
from apps.warehouse.core.services.package_types import package_types_service
from apps.warehouse.core.transformation import package_type_orm_to_schema
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.packaging import UnitOfMeasure

routes = Router(tags=["packaging"])


@routes.get("", response={200: GetPackageTypesResponse})
def get_package_types(request: HttpRequest, search_term: str | None = None):
    return GetPackageTypesResponse(
        data=[
            package_type_orm_to_schema(package_type)
            for package_type in package_types_service.get_package_types(search_term)
        ]
    )


@routes.get("/units", response={200: list[UnitOfMeasureSchema]})
@paginate(UnitOfMeasurePagination)
def get_units(request: HttpRequest, search_term: str | None = None):
    qs = cast(QuerySet[UnitOfMeasure], UnitOfMeasure.objects.select_related("base_uom"))
    if search_term:
        search_term = search_term.lower()
        qs = qs.filter(Q(name__icontains=search_term))

    return qs.all()


@routes.post("/units", response={200: GetUnitOfMeasureResponse})
def create_unit(request: HttpRequest, body: UnitOfMeasureCreateOrUpdateSchema):
    base_uom = None
    if body.base_uom:
        base_uom = UnitOfMeasure.objects.get(name=body.base_uom)

    unit, _ = UnitOfMeasure.objects.update_or_create(
        name=body.name,
        defaults={
            "amount_of_base_uom": body.amount_of_base_uom,
            "base_uom": base_uom,
        },
    )
    return GetUnitOfMeasureResponse(
        data=UnitOfMeasureSchema(
            created=unit.created,
            changed=unit.changed,
            name=unit.name,
            amount_of_base_uom=float(unit.amount_of_base_uom)
            if unit.amount_of_base_uom is not None
            else None,
            base_uom=unit.base_uom.name if unit.base_uom else None,
        )
    )


@routes.put("/units/{unit_name}", response={200: GetUnitOfMeasureResponse})
def update_unit(
    request: HttpRequest,
    unit_name: str,
    body: UnitOfMeasureCreateOrUpdateSchema,
):
    unit = UnitOfMeasure.objects.get(name=unit_name)
    base_uom = None
    if body.base_uom:
        base_uom = UnitOfMeasure.objects.get(name=body.base_uom)

    unit.name = body.name
    unit.amount_of_base_uom = body.amount_of_base_uom
    unit.base_uom = base_uom
    unit.save()
    return GetUnitOfMeasureResponse(
        data=UnitOfMeasureSchema(
            created=unit.created,
            changed=unit.changed,
            name=unit.name,
            amount_of_base_uom=float(unit.amount_of_base_uom)
            if unit.amount_of_base_uom is not None
            else None,
            base_uom=unit.base_uom.name if unit.base_uom else None,
        )
    )


@routes.post("/preview-package", response={200: PutInPackageResponse})
def package_preview(request: HttpRequest, body: PutInPackageRequestSchema):
    return PutInPackageResponse(
        data=warehouse_service.preview_packaging(
            body.order_item_id, body.product_code, body.package_name, body.amount
        )
    )


@routes.post("/preview-batch", response={200: PutInPackageResponse})
def batch_preview(request: HttpRequest, body: PutInBatchRequestSchema):
    return PutInPackageResponse(
        data=warehouse_service.preview_batching(
            order_item_id=body.order_item_id,
            product_code=body.product_code,
            amount=body.amount,
            batch_code=body.batch_code,
        )
    )


@routes.post("/preview-serial", response={200: PutInPackageResponse})
def serial_preview(request: HttpRequest, body: PutInSerialRequestSchema):
    return PutInPackageResponse(
        data=warehouse_service.preview_serial_tracking(
            order_item_id=body.order_item_id,
            product_code=body.product_code,
            amount=body.amount,
        )
    )


@routes.post("", response={200: GetPackageTypeResponse})
def create_package_type(
    request: HttpRequest,
    body: PackageTypeCreateOrUpdateSchema,
):
    return GetPackageTypeResponse(data=package_types_service.create_package_type(body))


@routes.put("/{package_type_name}", response={200: GetPackageTypeResponse})
def update_package_type(
    request: HttpRequest,
    package_type_name: str,
    body: PackageTypeCreateOrUpdateSchema,
):
    return GetPackageTypeResponse(
        data=package_types_service.update_package_type(package_type_name, body)
    )


@routes.delete("/{package_type_name}", response={200: DeletePackageTypeResponse})
def delete_package_type(request: HttpRequest, package_type_name: str):
    package_types_service.delete_package_type(package_type_name)
    return DeletePackageTypeResponse(success=True)
