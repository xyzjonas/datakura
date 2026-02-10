from __future__ import annotations

from typing import TYPE_CHECKING

from ninja import Schema

from .base import BaseResponse, BaseSchema, PaginatedResponse
from .base_orders import InboundWarehouseOrderBaseSchema, InboundOrderBaseSchema
from .credit_notes import CreditNoteSupplierSchema
from .product import ProductSchema
from ...models.warehouse import InboundWarehouseOrderState

if TYPE_CHECKING:
    pass


class WarehouseLocationSchema(BaseSchema):
    warehouse_name: str
    code: str
    #: mark a location as temporary for receiving or putaway
    is_putaway: bool


class PackageSchema(BaseSchema):
    type: str
    description: str | None = None
    amount: float
    unit: str | None = None


class WarehouseItemSchema(BaseSchema):
    """Atomic unit of the inventory - uniquely identifiable and trackable item in a warehouse"""

    id: int
    code: str
    product: ProductSchema
    unit_of_measure: str
    amount: float
    package: PackageSchema | None
    location: WarehouseLocationSchema


class ProductWarehouseAvailability(Schema):
    """Summary of item's availability in the warehouse"""

    total_amount: float
    available_amount: float


class WarehouseLocationDetailSchema(WarehouseLocationSchema):
    items: list[WarehouseItemSchema]


class WarehouseSchema(BaseSchema):
    name: str
    description: str | None
    locations: list[WarehouseLocationSchema]


class WarehouseExpandedSchema(BaseSchema):
    name: str
    description: str | None
    locations: list[WarehouseLocationDetailSchema]


class InboundWarehouseOrderSchema(InboundWarehouseOrderBaseSchema):
    items: list[WarehouseItemSchema]
    completed_items_count: int
    order: InboundOrderBaseSchema
    credit_note: CreditNoteSupplierSchema | None = None


class InboundWarehouseOrderUpdateSchema(Schema):
    state: InboundWarehouseOrderState


class InboundWarehouseOrderSetStateSchema(Schema):
    state: InboundWarehouseOrderState


class WarehouseOrderCreateSchema(Schema):
    purchase_order_code: str
    location_code: str


class WarehouseItemGetOrCreateSchema(Schema):
    code: str
    amount: float
    package_name: str | None
    location_code: str
    product_code: str


class GetWarehousesResponse(BaseResponse):
    data: list[WarehouseSchema]


class GetWarehouseLocationResponse(BaseResponse):
    data: WarehouseLocationDetailSchema


class GetProductWarehouseAvailabilityResponse(BaseResponse):
    data: ProductWarehouseAvailability


class GetProductWarehouseInfoResponse(BaseResponse):
    data: list[WarehouseExpandedSchema]


class GetWarehouseOrderResponse(BaseResponse):
    data: InboundWarehouseOrderSchema


class GetWarehouseOrdersResponse(PaginatedResponse[InboundWarehouseOrderSchema]):
    ...
    # data: list[WarehouseOrderSchema]


class UpdateWarehouseOrderDraftItemsRequest(Schema):
    to_be_removed: list[WarehouseItemSchema]
    to_be_added: list[WarehouseItemSchema]


class SetupTrackingWarehouseItemRequest(Schema):
    to_be_added: list[WarehouseItemSchema]


class RemoveItemToCreditNoteRequest(Schema):
    item_code: str
    amount: float
