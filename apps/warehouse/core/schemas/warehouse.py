from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from ninja import Schema

from .audit import AuditTimelineEntrySchema
from .barcode import BarcodeSchema
from .base import BaseResponse, BaseSchema, PaginatedResponse
from .base_orders import (
    InboundWarehouseOrderBaseSchema,
    InboundOrderBaseSchema,
    OutboundWarehouseOrderBaseSchema,
    OutboundOrderBaseSchema,
)
from .credit_notes import CreditNoteSupplierSchema
from .product import ProductSchema
from ...models.warehouse import (
    InboundWarehouseOrderState,
    OutboundWarehouseOrderState,
    TrackingLevel,
)

if TYPE_CHECKING:
    pass


class WarehouseLocationSchema(BaseSchema):
    warehouse_name: str
    code: str
    #: mark a location as temporary for receiving or putaway
    is_putaway: bool


class WarehouseLocationWithCountSchema(WarehouseLocationSchema):
    count: float


class PackageSchema(BaseSchema):
    type: str
    description: str | None = None
    amount: float
    unit: str | None = None


class BatchSchema(BaseSchema):
    id: int
    primary_barcode: BarcodeSchema | None = None
    description: str | None = None


class WarehouseItemSchema(BaseSchema):
    """Atomic unit of the inventory - uniquely identifiable and trackable item in a warehouse"""

    id: int
    product: ProductSchema
    unit_of_measure: str
    amount: float
    location: WarehouseLocationSchema
    tracking_level: TrackingLevel
    inbound_order_code: str | None = None
    outbound_order_code: str | None = None
    package: PackageSchema | None = None
    batch: BatchSchema | None = None
    primary_barcode: str | None = None


class WarehouseItemDetailSchema(WarehouseItemSchema):
    audits: list[AuditTimelineEntrySchema]


class WarehouseMovementSchema(Schema):
    moved_at: datetime
    location_from_code: str | None = None
    location_to_code: str | None = None
    stock_product: ProductSchema
    amount: float
    item: WarehouseItemSchema | None = None
    batch_id: int | None = None


class ProductWarehouseAvailability(Schema):
    """Summary of item's availability in the warehouse"""

    total_amount: Decimal
    available_amount: Decimal
    incoming_amount: Decimal


class WarehouseLocationDetailSchema(WarehouseLocationSchema):
    items: list[WarehouseItemSchema]


class WarehouseBaseSchema(BaseSchema):
    name: str
    description: str | None


class WarehouseSchema(WarehouseBaseSchema):
    locations: list[WarehouseLocationSchema]


class WarehouseWithCountsSchema(WarehouseBaseSchema):
    locations: list[WarehouseLocationWithCountSchema]


class WarehouseExpandedSchema(BaseSchema):
    name: str
    description: str | None
    locations: list[WarehouseLocationDetailSchema]


class InboundWarehouseOrderItemSchema(BaseSchema):
    """Frozen snapshot of a single line configured during order drafting."""

    id: int
    product: ProductSchema
    unit_of_measure: str
    amount: Decimal
    tracking_level: TrackingLevel
    package: PackageSchema | None
    unit_price_at_receipt: Decimal
    index: int
    batch_barcode: str | None
    pending: bool
    warehouse_item_id: int | None = None
    outbound_order_code: str | None = None


class DraftItemAddSchema(Schema):
    """Payload for adding a line item to a draft inbound warehouse order."""

    product_code: str
    amount: float


class InboundWarehouseOrderSchema(InboundWarehouseOrderBaseSchema):
    order_items: list[InboundWarehouseOrderItemSchema]
    items: list[WarehouseItemSchema]
    movements: list[WarehouseMovementSchema]
    completed_items_count: int
    total_amount: float
    remaining_amount: float
    order: InboundOrderBaseSchema
    credit_note: CreditNoteSupplierSchema | None = None


class OutboundWarehouseOrderSchema(OutboundWarehouseOrderBaseSchema):
    order_items: list["OutboundWarehouseOrderItemSchema"]
    items: list[WarehouseItemSchema]
    movements: list[WarehouseMovementSchema]
    completed_items_count: int
    total_amount: float
    remaining_amount: float
    order: OutboundOrderBaseSchema


class OutboundWarehouseOrderItemSchema(BaseSchema):
    id: int
    product: ProductSchema
    unit_of_measure: str
    amount: Decimal
    desired_package_type_name: str | None
    desired_batch_code: str | None
    warehouse_item_id: int | None = None
    warehouse_item: WarehouseItemSchema | None = None
    pending: bool
    index: int


class InboundWarehouseOrderUpdateSchema(Schema):
    state: InboundWarehouseOrderState


class InboundWarehouseOrderSetStateSchema(Schema):
    location_code: str | None = None


class OutboundWarehouseOrderUpdateSchema(Schema):
    state: OutboundWarehouseOrderState


class OutboundWarehouseOrderSetStateSchema(Schema):
    state: OutboundWarehouseOrderState
    location_code: str | None = None


class WarehouseOrderCreateSchema(Schema):
    purchase_order_code: str


class WarehouseItemGetOrCreateSchema(Schema):
    code: str
    amount: float
    package_name: str | None
    location_code: str
    product_code: str


class GetWarehousesResponse(BaseResponse):
    data: list[WarehouseSchema]


class GetWarehousesWithCountsResponse(BaseResponse):
    data: list[WarehouseWithCountsSchema]


class GetWarehouseLocationsResponse(PaginatedResponse[WarehouseLocationSchema]): ...


class GetWarehouseLocationResponse(BaseResponse):
    data: WarehouseLocationDetailSchema


class GetProductWarehouseAvailabilityResponse(BaseResponse):
    data: ProductWarehouseAvailability


class GetProductWarehouseInfoResponse(BaseResponse):
    data: list[WarehouseExpandedSchema]


class GetWarehouseOrderResponse(BaseResponse):
    data: InboundWarehouseOrderSchema


class GetOutboundWarehouseOrderResponse(BaseResponse):
    data: OutboundWarehouseOrderSchema


class GetWarehouseItemResponse(BaseResponse):
    data: WarehouseItemDetailSchema


class GetWarehouseOrdersResponse(PaginatedResponse[InboundWarehouseOrderSchema]):
    ...
    # data: list[WarehouseOrderSchema]


class GetOutboundWarehouseOrdersResponse(
    PaginatedResponse[OutboundWarehouseOrderSchema]
): ...


class UpdateWarehouseOrderDraftItemsRequest(Schema):
    to_be_removed: list[int]  # IDs of InboundWarehouseOrderItem
    to_be_added: list[DraftItemAddSchema]


class SetupTrackingWarehouseItemRequest(Schema):
    to_be_added: list[WarehouseItemSchema]


class RemoveItemToCreditNoteRequest(Schema):
    item_id: int
    amount: float


class PutawayItemRequest(Schema):
    new_location_code: str


class CreateWarehouseMovementSchema(Schema):
    item_id: int
    warehouse_order_code: str
    new_location_code: str


class OffloadItemSchema(Schema):
    item_id: int
    amount: float


class OffloadItemsToChildOrderRequest(Schema):
    items: list[OffloadItemSchema]


class AssignOutboundWarehouseOrderItemRequest(Schema):
    warehouse_item_id: int


class GetOutboundWarehouseOrderItemCandidatesResponse(BaseResponse):
    data: list[WarehouseItemSchema]
