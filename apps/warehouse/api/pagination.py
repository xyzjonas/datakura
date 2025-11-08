from __future__ import annotations

from django.db.models import QuerySet
from ninja import Schema
from ninja.pagination import PaginationBase

from apps.warehouse.api.schemas.customer import (
    GetCustomersResponse,
)
from apps.warehouse.api.schemas.product import (
    GetProductsResponse,
)
from apps.warehouse.core.transformation import (
    customer_orm_to_schema,
    product_orm_to_schema,
)
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.product import StockProduct


class StockProductPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetProductsResponse): ...

    def paginate_queryset(
        self, queryset: QuerySet[StockProduct], pagination: Input, **params
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [product_orm_to_schema(product) for product in items],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class CustomersPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetCustomersResponse): ...

    def paginate_queryset(
        self, queryset: QuerySet[Customer], pagination: Input, **params
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [customer_orm_to_schema(customer) for customer in items],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }
