"""
Logic shared by sales orders (`OutboundOrder`) and their pre-stage, calculations
(`OutboundCalculation`): both have the very same items and pricing rules.

Everything here is duck-typed on "a document with `customer` and `items`".
"""

from calendar import monthrange
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal, TypeVar

from pydantic import BaseModel

from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.core.packaging import get_package_amount_in_product_uom
from apps.warehouse.core.query_optimization import outbound_orders_for_schema
from apps.warehouse.core.schemas.orders import (
    OutboundOrderSchema,
    OutboundDocumentSchema,
    OutboundOrderItemPricingDetailsSchema,
)
from apps.warehouse.core.services.products import stock_product_service
from apps.warehouse.core.services.settings import MinimumItemValue, settings_service
from apps.warehouse.core.transformation import outbound_order_orm_to_schema
from apps.warehouse.models.barcode import Barcode
from apps.warehouse.models.customer import ContactPerson, Customer
from apps.warehouse.models.orders import OutboundCalculation, OutboundOrder
from apps.warehouse.models.packaging import PackageType
from apps.warehouse.models.product import StockProduct, StockProductPrice
from apps.warehouse.models.warehouse import Batch

OutboundDocument = OutboundOrder | OutboundCalculation
DocumentSchemaT = TypeVar("DocumentSchemaT", bound=OutboundDocumentSchema)


def _get_end_of_month(date: datetime) -> datetime:
    last_day = monthrange(date.year, date.month)[1]
    return date.replace(day=last_day)


def _get_month_range(date: datetime) -> tuple[datetime, datetime]:
    last_day = _get_end_of_month(date)
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0), last_day


def diff_schemas(previous: BaseModel, current: BaseModel) -> dict[str, dict[str, str]]:
    """Field-by-field `{old, new}` diff of two read schemas, for the audit trail."""
    new_values = current.model_dump()
    return {
        key: {"old": str(value), "new": str(new_values[key])}
        for key, value in previous.model_dump().items()
        if key not in ("created", "changed") and value != new_values[key]
    }


def get_customer_contact_or_none(
    customer: Customer, contact_id: int | None
) -> ContactPerson | None:
    if contact_id is None:
        return None
    contact = ContactPerson.objects.filter(
        id=contact_id, customer=customer, is_deleted=False
    ).first()
    if contact is None:
        raise WarehouseItemBadRequestError(
            f"Contact '{contact_id}' does not belong to customer '{customer.code}'."
        )
    return contact


def get_desired_package_or_none(name: str | None) -> PackageType | None:
    if not name:
        return None
    return PackageType.objects.get(name=name)


def get_desired_batch_or_none(batch_code: str | None) -> Batch | None:
    if not batch_code:
        return None

    barcode = (
        Barcode.objects.select_related("content_type").filter(code=batch_code).first()
    )
    if not barcode or barcode.content_type.model_class() is not Batch:
        raise WarehouseItemBadRequestError(f"Batch '{batch_code}' does not exist.")
    return barcode.content_object  # type: ignore[return-value]


def validate_desired_packaging(
    *,
    stock_product: StockProduct,
    amount: Decimal,
    desired_package_type: PackageType | None,
) -> None:
    if desired_package_type is None:
        return

    package_amount = get_package_amount_in_product_uom(
        desired_package_type, stock_product
    )
    if not package_amount:
        raise WarehouseItemBadRequestError(
            f"Package '{desired_package_type.name}' cannot be converted to product '{stock_product.code}'."
        )

    normalized_package_amount = Decimal(str(package_amount))
    if normalized_package_amount <= 0:
        raise WarehouseItemBadRequestError(
            f"Package '{desired_package_type.name}' has invalid amount."
        )

    if amount % normalized_package_amount != 0:
        raise WarehouseItemBadRequestError(
            f"Requested amount '{amount}' does not fit package '{desired_package_type.name}'."
        )


def compute_unit_price(amount: Decimal, total_price: Decimal) -> Decimal:
    if amount <= 0:
        return Decimal("0")
    return (total_price / amount).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def build_item_pricing_details(
    *,
    order: OutboundDocument,
    stock_product: StockProduct,
    selected_unit_price: Decimal,
    total_price: Decimal,
    customer_overrides: dict[int, StockProductPrice] | None = None,
    minimum: MinimumItemValue | None | Literal["resolve"] = "resolve",
) -> OutboundOrderItemPricingDetailsSchema:
    """
    `customer_overrides` / `minimum` are per-order constants: pass them in when
    building details for many items, otherwise they are looked up for each call.
    """
    suggested = stock_product_service.build_selling_price_lookup(
        stock_product, order.customer, customer_overrides
    )

    reason = suggested.reason
    if minimum == "resolve":
        minimum = settings_service.resolve_minimum_item_value(order.customer)
    if minimum is not None and total_price == minimum.value:
        reason = f"{reason}; {minimum.explanation}"

    avg_purchase_price = Decimal(str(stock_product.purchase_price or 0))
    margin_amount = selected_unit_price - avg_purchase_price
    margin_percent = Decimal("0")
    if avg_purchase_price > 0:
        margin_percent = (margin_amount / avg_purchase_price * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return OutboundOrderItemPricingDetailsSchema(
        base_price=suggested.base_price,
        avg_purchase_price=float(avg_purchase_price),
        suggested_unit_price=suggested.final_price,
        selected_unit_price=float(selected_unit_price),
        discount_percent=suggested.discount_percent,
        reason=reason,
        source=suggested.source,
        margin_amount=float(
            margin_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        ),
        margin_percent=float(margin_percent),
    )


def with_pricing_details(
    schema: DocumentSchemaT, order_model: OutboundDocument
) -> DocumentSchemaT:
    # `.all()` serves from the prefetch cache when the order was loaded with items
    products = {
        item.stock_product.code: item.stock_product for item in order_model.items.all()
    }
    customer = order_model.customer
    # per-order constants, resolved once instead of once per item
    customer_overrides = (
        stock_product_service.get_customer_overrides(customer, products.values())
        if customer
        else None
    )
    minimum = settings_service.resolve_minimum_item_value(customer)
    for schema_item in schema.items:
        product = products.get(schema_item.product.code)
        if product is None:
            continue
        schema_item.pricing_details = build_item_pricing_details(
            order=order_model,
            stock_product=product,
            selected_unit_price=Decimal(str(schema_item.unit_price)),
            total_price=Decimal(str(schema_item.total_price)),
            customer_overrides=customer_overrides,
            minimum=minimum,
        )
    return schema


def outbound_order_schema(order: OutboundOrder) -> OutboundOrderSchema:
    """
    Read schema of the sales order (without pricing details). Re-loads the order with
    everything the serialization needs, so the cost doesn't grow with its items.
    """
    return outbound_order_orm_to_schema(outbound_orders_for_schema().get(pk=order.pk))


def outbound_order_schema_with_pricing(order: OutboundOrder) -> OutboundOrderSchema:
    """Like `outbound_order_schema`, including per-item pricing details."""
    loaded = outbound_orders_for_schema().get(pk=order.pk)
    return with_pricing_details(outbound_order_orm_to_schema(loaded), loaded)
