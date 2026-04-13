from __future__ import annotations

from django.db import transaction

from apps.warehouse.core.schemas.customer import CustomerGroupCreateOrUpdateSchema
from apps.warehouse.core.transformation import customer_group_orm_to_schema
from apps.warehouse.models.customer import CustomerGroup


class CustomerGroupsService:
    @staticmethod
    @transaction.atomic
    def create_group(params: CustomerGroupCreateOrUpdateSchema):
        group, _ = CustomerGroup.objects.get_or_create(
            code=params.code,
            defaults={"name": params.name},
        )
        if group.name != params.name:
            group.name = params.name
            group.save(update_fields=["name", "changed"])
        return customer_group_orm_to_schema(group)

    @staticmethod
    @transaction.atomic
    def update_group(group_code: str, params: CustomerGroupCreateOrUpdateSchema):
        group = CustomerGroup.objects.get(code=group_code)
        group.code = params.code
        group.name = params.name
        group.save(update_fields=["code", "name", "changed"])
        return customer_group_orm_to_schema(group)

    @staticmethod
    @transaction.atomic
    def delete_group(group_code: str):
        group = CustomerGroup.objects.get(code=group_code)
        schema = customer_group_orm_to_schema(group)
        group.delete()
        return schema


customer_groups_service = CustomerGroupsService()
