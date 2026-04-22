from __future__ import annotations

from django.db import transaction
from django.db.models import Q, QuerySet

from apps.warehouse.core.schemas.packaging import PackageTypeCreateOrUpdateSchema
from apps.warehouse.core.transformation import package_type_orm_to_schema
from apps.warehouse.models.packaging import PackageType, UnitOfMeasure


class PackageTypesService:
    @staticmethod
    def get_package_types(search_term: str | None = None) -> QuerySet[PackageType]:
        qs = PackageType.objects.select_related("unit_of_measure")
        if search_term:
            qs = qs.filter(
                Q(name__icontains=search_term)
                | Q(description__icontains=search_term)
                | Q(unit_of_measure__name__icontains=search_term)
            )
        return qs.order_by("name")

    @staticmethod
    @transaction.atomic
    def create_package_type(params: PackageTypeCreateOrUpdateSchema):
        unit_of_measure = None
        if params.unit:
            unit_of_measure = UnitOfMeasure.objects.get(name=params.unit)

        package_type, _ = PackageType.objects.update_or_create(
            name=params.name,
            defaults={
                "description": params.description,
                "amount": params.amount,
                "unit_of_measure": unit_of_measure,
            },
        )
        return package_type_orm_to_schema(package_type)

    @staticmethod
    @transaction.atomic
    def update_package_type(name: str, params: PackageTypeCreateOrUpdateSchema):
        package_type = PackageType.objects.select_related("unit_of_measure").get(
            name=name
        )
        unit_of_measure = None
        if params.unit:
            unit_of_measure = UnitOfMeasure.objects.get(name=params.unit)

        package_type.name = params.name
        package_type.description = params.description
        package_type.amount = params.amount
        package_type.unit_of_measure = unit_of_measure
        package_type.save(
            update_fields=[
                "name",
                "description",
                "amount",
                "unit_of_measure",
                "changed",
            ]
        )
        return package_type_orm_to_schema(package_type)

    @staticmethod
    @transaction.atomic
    def delete_package_type(name: str) -> None:
        PackageType.objects.get(name=name).delete()


package_types_service = PackageTypesService()
