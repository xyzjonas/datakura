from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from apps.warehouse.core.schemas.packaging import (
    GetPackageTypesResponse,
    PackageTypeSchema,
    PutInPackageRequestSchema,
    PutInPackageResponse,
)
from apps.warehouse.core.services.warehouse import warehouse_service
from apps.warehouse.models.packaging import PackageType

routes = Router(tags=["packaging"])


@routes.get("", response={200: GetPackageTypesResponse}, auth=None)
def get_package_types(request: HttpRequest, search_term: str | None = None):
    return GetPackageTypesResponse(
        data=[
            PackageTypeSchema(
                created=package_type.created,
                changed=package_type.changed,
                name=package_type.name,
                amount=float(package_type.amount),
                description=package_type.description,
                unit=package_type.unit_of_measure.name,
            )
            for package_type in PackageType.objects.prefetch_related(
                "unit_of_measure"
            ).all()
        ]
    )


@routes.post("/", response={200: PutInPackageResponse}, auth=None)
def package_preview(request: HttpRequest, body: PutInPackageRequestSchema):
    return PutInPackageResponse(
        data=warehouse_service.preview_packaging(
            body.warehouse_item_id, body.product_code, body.package_name, body.amount
        )
    )
