from __future__ import annotations

from django.db.models import QuerySet
from django.http.request import HttpRequest
from ninja import Schema
from ninja.pagination import PaginationBase

from apps.warehouse.core.schemas.credit_notes import GetCreditNotesToSupplierResponse
from apps.warehouse.core.schemas.customer import (
    GetCustomersResponse,
    GetCustomerGroupsResponse,
)
from apps.warehouse.core.schemas.analytics import (
    GetInventorySnapshotsResponse,
    GetWarehouseMovementsResponse,
)
from apps.warehouse.core.schemas.group import (
    GetProductGroupsResponse,
)
from apps.warehouse.core.schemas.type import (
    GetProductTypesResponse,
)
from apps.warehouse.core.schemas.manufacturing import ManufacturingOrderSchema
from apps.warehouse.core.schemas.orders import GetInboundOrdersResponse
from apps.warehouse.core.schemas.orders import GetOutboundOrdersResponse
from apps.warehouse.core.schemas.invoice import (
    GetInvoicePaymentMethodsResponse,
    GetInvoicesResponse,
)
from apps.warehouse.core.schemas.packaging import (
    BatchSchema,
    GetBatchesResponse,
    GetUnitOfMeasuresResponse,
    UnitOfMeasureSchema,
)
from apps.warehouse.core.schemas.product import (
    GetProductsResponse,
)
from apps.warehouse.core.schemas.warehouse import (
    GetWarehouseOrdersResponse,
    GetOutboundWarehouseOrdersResponse,
    GetWarehouseLocationsResponse,
)
from apps.warehouse.core.transformation import (
    customer_orm_to_schema,
    customer_group_orm_to_schema,
    product_orm_to_schema,
    product_group_orm_to_schema,
    product_type_orm_to_schema,
    inbound_order_orm_to_schema,
    outbound_order_orm_to_schema,
    warehouse_inbound_order_orm_to_schema,
    warehouse_outbound_order_orm_to_schema,
    credit_note_supplier_orm_to_schema,
    location_orm_to_schema,
    invoice_payment_method_orm_to_schema,
    invoice_orm_to_schema,
    barcode_orm_to_schema,
)
from apps.warehouse.core.services.inventory_snapshots import inventory_snapshot_service
from apps.warehouse.core.transformation import manufacturing_order_orm_to_schema
from apps.warehouse.models.customer import Customer, CustomerGroup
from apps.warehouse.models.manufacturing import ManufacturingOrder
from apps.warehouse.models.orders import (
    InboundOrder,
    OutboundOrder,
    CreditNoteToSupplier,
    Invoice,
    InvoicePaymentMethod,
)
from apps.warehouse.models.product import StockProduct, ProductGroup, ProductType
from apps.warehouse.models.packaging import UnitOfMeasure
from apps.warehouse.models.warehouse import (
    Batch,
    InventorySnapshot,
    InboundWarehouseOrder,
    OutboundWarehouseOrder,
    WarehouseLocation,
    WarehouseMovement,
)


class InventorySnapshotsPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetInventorySnapshotsResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[InventorySnapshot],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [
                inventory_snapshot_service._to_summary_schema(snapshot)
                for snapshot in items
            ],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class StockProductPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetProductsResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[StockProduct],
        pagination: Input,
        request: HttpRequest,
        **params,
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
        self,
        queryset: QuerySet[Customer],
        pagination: Input,
        request: HttpRequest,
        **params,
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


class CustomerGroupsPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetCustomerGroupsResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[CustomerGroup],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [customer_group_orm_to_schema(group) for group in items],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class IncomingOrdersPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetInboundOrdersResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[InboundOrder],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [inbound_order_orm_to_schema(order) for order in items],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class OutgoingOrdersPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetOutboundOrdersResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[OutboundOrder],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [outbound_order_orm_to_schema(order) for order in items],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class InvoicesPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetInvoicesResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[Invoice],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [invoice_orm_to_schema(invoice) for invoice in items],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class IncomingWarehouseOrdersPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetWarehouseOrdersResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[InboundWarehouseOrder],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [warehouse_inbound_order_orm_to_schema(order) for order in items],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class OutgoingWarehouseOrdersPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetOutboundWarehouseOrdersResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[OutboundWarehouseOrder],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [warehouse_outbound_order_orm_to_schema(order) for order in items],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class CreditNoteToSupplierPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetCreditNotesToSupplierResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[CreditNoteToSupplier],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [
                credit_note_supplier_orm_to_schema(credit_note) for credit_note in items
            ],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class WarehouseLocationsPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetWarehouseLocationsResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[WarehouseLocation],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [location_orm_to_schema(location) for location in items],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class ProductGroupPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetProductGroupsResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[ProductGroup],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [product_group_orm_to_schema(group) for group in items],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class ProductTypePagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetProductTypesResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[ProductType],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [
                product_type_orm_to_schema(product_type) for product_type in items
            ],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class UnitOfMeasurePagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetUnitOfMeasuresResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[UnitOfMeasure],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [
                UnitOfMeasureSchema(
                    created=item.created,
                    changed=item.changed,
                    name=item.name,
                    amount_of_base_uom=float(item.amount_of_base_uom)
                    if item.amount_of_base_uom is not None
                    else None,
                    base_uom=item.base_uom.name if item.base_uom else None,
                )
                for item in items
            ],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class InvoicePaymentMethodPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetInvoicePaymentMethodsResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[InvoicePaymentMethod],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [
                invoice_payment_method_orm_to_schema(payment_method)
                for payment_method in items
            ],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class BatchesPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetBatchesResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[Batch],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [
                BatchSchema(
                    id=batch.pk,
                    created=batch.created,
                    changed=batch.changed,
                    primary_barcode=barcode_orm_to_schema(batch.get_primary_barcode())
                    if batch.get_primary_barcode()
                    else None,
                    description=batch.description,
                )
                for batch in items
            ],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class ManufacturingOrdersPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(Schema):
        data: list[ManufacturingOrderSchema]
        count: int
        next: int | None
        previous: int | None
        success: bool = True

    def paginate_queryset(
        self,
        queryset: QuerySet[ManufacturingOrder],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [manufacturing_order_orm_to_schema(order) for order in items],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }


class WarehouseMovementsPagination(PaginationBase):
    items_attribute: str = "data"

    class Input(Schema):
        page: int = 1
        page_size: int = 20

    class Output(GetWarehouseMovementsResponse): ...

    def paginate_queryset(
        self,
        queryset: QuerySet[WarehouseMovement],
        pagination: Input,
        request: HttpRequest,
        **params,
    ):
        from apps.warehouse.core.services.movements import movement_service

        offset = (pagination.page - 1) * pagination.page_size
        items = queryset[offset : offset + pagination.page_size]
        count = queryset.count()

        return {
            "data": [
                movement_service.movement_to_schema(movement) for movement in items
            ],
            "count": count,
            "next": pagination.page + 1
            if offset + pagination.page_size < count
            else None,
            "previous": pagination.page - 1 if pagination.page > 1 else None,
        }
