"""
Reusable `select_related` / `Prefetch` building blocks, matching what the
`*_orm_to_schema` functions in `transformation.py` read.

Rule of thumb: whatever a transformation touches per item/row has to be loaded here,
otherwise serializing an order costs a few queries *per item* (N+1).
"""

from django.db.models import Prefetch, QuerySet

from apps.warehouse.models.orders import (
    InboundOrder,
    OutboundCalculation,
    OutboundOrder,
)
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    Batch,
    InboundWarehouseOrder,
    InboundWarehouseOrderItem,
    OutboundWarehouseOrder,
    OutboundWarehouseOrderItem,
    WarehouseItem,
    WarehouseMovement,
)

# `customer_orm_to_base_schema` (embedded in every order)
CUSTOMER_BASE_RELATED = ("customer_group", "discount_group", "default_payment_method")
# `customer_orm_to_schema` (embedded in invoices)
CUSTOMER_FULL_RELATED = (*CUSTOMER_BASE_RELATED, "owner", "responsible_user")


def invoice_related(prefix: str = "invoice") -> tuple[str, ...]:
    """`select_related` paths for `invoice_orm_to_schema` (use with the contacts prefetch)."""
    paths = [prefix, f"{prefix}__payment_method"]
    for side in ("customer", "supplier"):
        paths.append(f"{prefix}__{side}")
        paths.extend(f"{prefix}__{side}__{rel}" for rel in CUSTOMER_FULL_RELATED)
    return tuple(paths)


def invoice_prefetch(prefix: str = "invoice") -> tuple[str, ...]:
    return (f"{prefix}__customer__contacts", f"{prefix}__supplier__contacts")


def customer_related(prefix: str) -> tuple[str, ...]:
    """`select_related` paths of a customer FK, e.g. `customer_related("customer")`."""
    return (prefix, *(f"{prefix}__{rel}" for rel in CUSTOMER_BASE_RELATED))


def product_prefetch(lookup: str) -> Prefetch:
    """
    Everything `product_orm_to_schema` reads of the product behind `lookup`
    (e.g. `"stock_product"` or `"items__stock_product"`): type, unit, group,
    dynamic prices (+customers) and barcodes - a constant number of queries.
    """
    return Prefetch(
        lookup,
        queryset=StockProduct.objects.select_related(
            "type", "unit_of_measure__base_uom", "group"
        )
        .prefetch_related("dynamic_prices__customer")
        .with_barcodes(),
    )


def batch_prefetch(lookup: str) -> Prefetch:
    """A batch FK (e.g. `"desired_batch"`) with its barcodes."""
    return Prefetch(
        lookup,
        queryset=Batch.objects.select_related("certification").with_barcodes(),
    )


def warehouse_item_prefetch(lookup: str) -> list[Prefetch]:
    """
    Everything `warehouse_item_orm_to_schema` reads of the item(s) behind `lookup`
    (e.g. `"items"`, `"order_items__warehouse_item"`, `"warehouse_movements__item"`).
    """
    return [
        Prefetch(
            lookup,
            queryset=WarehouseItem.objects.select_related(
                "location__warehouse",
                "package_type__unit_of_measure__base_uom",
                "order_in",
                "outbound_assignment__warehouse_order",
            ).with_barcodes(),
        ),
        product_prefetch(f"{lookup}__stock_product"),
        batch_prefetch(f"{lookup}__batch"),
    ]


def _movements_prefetch() -> list[str | Prefetch]:
    return [
        Prefetch(
            "warehouse_movements",
            queryset=WarehouseMovement.objects.select_related(
                "location_from", "location_to"
            ),
        ),
        product_prefetch("warehouse_movements__stock_product"),
        *warehouse_item_prefetch("warehouse_movements__item"),
    ]


def outbound_warehouse_orders_for_schema(
    queryset: "QuerySet[OutboundWarehouseOrder] | None" = None,
) -> "QuerySet[OutboundWarehouseOrder]":
    """Picking orders ready for `warehouse_outbound_order_orm_to_schema`."""
    qs = OutboundWarehouseOrder.objects.all() if queryset is None else queryset
    return qs.select_related(
        *customer_related("order__customer"),
        *customer_related("order__supplier"),
        *customer_related("manufacturing_order__customer"),
        *customer_related("manufacturing_order__supplier"),
        "primary_order",
        "primary_order__order",
    ).prefetch_related(
        Prefetch(
            "order_items",
            queryset=OutboundWarehouseOrderItem.objects.select_related(
                "desired_package_type"
            ),
        ),
        product_prefetch("order_items__stock_product"),
        batch_prefetch("order_items__desired_batch"),
        *warehouse_item_prefetch("order_items__warehouse_item"),
        Prefetch(
            "derived_orders",
            queryset=OutboundWarehouseOrder.objects.select_related("order"),
        ),
        *_movements_prefetch(),
    )


def _credit_note_prefetch(prefix: str) -> list[str | Prefetch]:
    return [
        f"{prefix}__items",
        product_prefetch(f"{prefix}__items__stock_product"),
    ]


def outbound_orders_for_schema(
    queryset: "QuerySet[OutboundOrder] | None" = None,
) -> "QuerySet[OutboundOrder]":
    """Sales orders ready for `outbound_order_orm_to_schema` (+ `with_pricing_details`)."""
    qs = OutboundOrder.objects.all() if queryset is None else queryset
    return qs.select_related(
        *customer_related("customer"),
        *customer_related("supplier"),
        "contact",
        "calculation",
        "shipping__shipping_type",
        "credit_note",
        *invoice_related(),
    ).prefetch_related(
        "items__desired_package_type",
        product_prefetch("items__stock_product"),
        batch_prefetch("items__desired_batch"),
        Prefetch(
            "warehouse_orders",
            queryset=OutboundWarehouseOrder.objects.select_related(
                "order", "primary_order", "primary_order__order"
            ),
        ),
        Prefetch(
            "warehouse_orders__derived_orders",
            queryset=OutboundWarehouseOrder.objects.select_related("order"),
        ),
        *_credit_note_prefetch("credit_note"),
        *invoice_prefetch(),
    )


def outbound_calculations_for_schema(
    queryset: "QuerySet[OutboundCalculation] | None" = None,
) -> "QuerySet[OutboundCalculation]":
    """Calculations ready for `outbound_calculation_orm_to_schema`."""
    qs = OutboundCalculation.objects.all() if queryset is None else queryset
    return qs.select_related(
        *customer_related("customer"),
        *customer_related("supplier"),
        "contact",
        "order",
    ).prefetch_related(
        "items__desired_package_type",
        product_prefetch("items__stock_product"),
        batch_prefetch("items__desired_batch"),
    )


def inbound_orders_for_schema(
    queryset: "QuerySet[InboundOrder] | None" = None,
) -> "QuerySet[InboundOrder]":
    """Purchase orders ready for `inbound_order_orm_to_schema`."""
    qs = InboundOrder.objects.all() if queryset is None else queryset
    parent_paths = ("order", "manufacturing_order")
    return qs.select_related(
        *customer_related("customer"),
        *customer_related("supplier"),
        "credit_note",
        *invoice_related(),
    ).prefetch_related(
        product_prefetch("items__stock_product"),
        "items__certification",
        batch_prefetch("items__certification__batches"),
        batch_prefetch("items__batch"),
        Prefetch(
            "warehouse_orders",
            queryset=InboundWarehouseOrder.objects.select_related(
                *parent_paths,
                "primary_order",
                *(f"primary_order__{p}" for p in parent_paths),
            ),
        ),
        Prefetch(
            "warehouse_orders__derived_orders",
            queryset=InboundWarehouseOrder.objects.select_related(*parent_paths),
        ),
        *_credit_note_prefetch("credit_note"),
        *invoice_prefetch(),
    )


def inbound_warehouse_orders_for_schema(
    queryset: "QuerySet[InboundWarehouseOrder] | None" = None,
) -> "QuerySet[InboundWarehouseOrder]":
    """Receiving orders ready for `warehouse_inbound_order_orm_to_schema`."""
    qs = InboundWarehouseOrder.objects.all() if queryset is None else queryset
    parent_paths = ("order", "manufacturing_order")
    return qs.select_related(
        *customer_related("order__customer"),
        *customer_related("order__supplier"),
        *customer_related("manufacturing_order__customer"),
        *customer_related("manufacturing_order__supplier"),
        "order__credit_note",
        "primary_order",
        *(f"primary_order__{p}" for p in parent_paths),
    ).prefetch_related(
        Prefetch(
            "order_items",
            queryset=InboundWarehouseOrderItem.objects.select_related(
                "package_type__unit_of_measure"
            ),
        ),
        product_prefetch("order_items__stock_product"),
        Prefetch(
            "order_items__warehouse_items",
            queryset=WarehouseItem.objects.select_related(
                "location", "outbound_assignment__warehouse_order"
            ),
        ),
        *warehouse_item_prefetch("items"),
        "order__items",
        "manufacturing_order__items",
        Prefetch(
            "derived_orders",
            queryset=InboundWarehouseOrder.objects.select_related(*parent_paths),
        ),
        *_credit_note_prefetch("order__credit_note"),
        *_movements_prefetch(),
    )
