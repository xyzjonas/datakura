from __future__ import annotations

from typing import cast

from django.db.models import F

from apps.warehouse.core.schemas.base_orders import (
    InboundWarehouseOrderBaseSchema,
    InboundOrderBaseSchema,
)
from apps.warehouse.core.schemas.customer import (
    CustomerSchema,
    CustomerGroupSchema,
    ContactPersonSchema,
)
from apps.warehouse.core.schemas.orders import (
    InboundOrderSchema,
    InboundOrderItemSchema,
    CreditNoteSupplierSchema,
    CreditNoteSupplierItemSchema,
)
from apps.warehouse.core.schemas.product import ProductSchema
from apps.warehouse.core.schemas.warehouse import (
    WarehouseItemSchema,
    PackageSchema,
    InboundWarehouseOrderSchema,
    WarehouseLocationSchema,
    WarehouseLocationDetailSchema,
)
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderItem,
    InboundOrderState,
    CreditNoteToSupplier,
    CreditNoteState,
)
from apps.warehouse.models.packaging import PackageType
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    WarehouseItem,
    InboundWarehouseOrder,
    WarehouseLocation,
    InboundWarehouseOrderState,
)


def location_orm_to_schema(location: WarehouseLocation) -> WarehouseLocationSchema:
    return WarehouseLocationSchema(
        warehouse_name=location.warehouse.name,
        code=location.code,
        changed=location.changed,
        created=location.created,
        is_putaway=location.is_putaway,
    )


def location_orm_to_detail_schema(
    location: WarehouseLocation, include_draft_items: bool = False
) -> WarehouseLocationDetailSchema:
    items_qs = location.items
    if not include_draft_items:
        items_qs = items_qs.exclude(order_in__state=InboundWarehouseOrderState.DRAFT)
    return WarehouseLocationDetailSchema(
        **location_orm_to_schema(location).model_dump(),
        items=[warehouse_item_orm_to_schema(item) for item in items_qs.all()],
    )


def customer_orm_to_schema(customer: Customer) -> CustomerSchema:
    return CustomerSchema(
        created=customer.created,
        changed=customer.changed,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        code=customer.code,
        street=customer.street,
        city=customer.city,
        postal_code=customer.postal_code,
        state=customer.state,
        tax_identification=customer.tax_identification,
        identification=customer.identification,
        customer_type=customer.customer_type,
        price_type=customer.price_type,
        invoice_due_days=customer.invoice_due_days,
        block_after_due_days=customer.block_after_due_days,
        data_collection_agreement=customer.data_collection_agreement,
        marketing_data_use_agreement=customer.marketing_data_use_agreement,
        is_valid=customer.is_valid,
        is_deleted=customer.is_deleted,
        owner=customer.owner.username if customer.owner else None,
        responsible_user=customer.responsible_user.username
        if customer.responsible_user
        else None,
        group=CustomerGroupSchema.from_orm(customer.customer_group),
        contacts=[
            ContactPersonSchema.from_orm(contact) for contact in customer.contacts.all()
        ],
        note=customer.note,
        register_information=customer.register_information,
    )


def product_orm_to_schema(product: StockProduct) -> ProductSchema:
    return ProductSchema(
        name=product.name,
        code=product.code,
        type=product.type.name,
        unit=product.unit_of_measure.name,
        group=product.group.name if product.group else None,
        created=product.created,
        changed=product.changed,
        unit_weight=float(product.unit_weight),
        currency=product.currency,
        base_price=float(product.base_price),
        purchase_price=float(product.purchase_price),
        customs_declaration_group=product.customs_declaration_group,
        attributes=product.attributes,
    )


def get_product_by_code(product_code: str) -> ProductSchema:
    product = StockProduct.objects.prefetch_related(
        "unit_of_measure", "type", "group"
    ).get(code=product_code)
    return product_orm_to_schema(product)


def package_orm_to_schema(package_type: PackageType | None) -> PackageSchema | None:
    if package_type is None:
        return None
    return PackageSchema(
        changed=package_type.changed,
        created=package_type.created,
        unit=package_type.unit_of_measure.name
        if package_type.unit_of_measure
        else None,
        type=package_type.name,
        description=package_type.description,
        amount=float(package_type.amount),
    )


def warehouse_item_orm_to_schema(item: WarehouseItem) -> WarehouseItemSchema:
    amount = float(item.amount) if item.amount else None
    package_type = package_orm_to_schema(item.package_type)
    if package_type and package_type.unit and item.package_amount_in_product_uom:
        package_type.amount = item.package_amount_in_product_uom
        if amount is None:
            amount = package_type.amount

    return WarehouseItemSchema(
        id=item.pk,
        code=item.code,
        package=package_type,
        product=product_orm_to_schema(item.stock_product),
        unit_of_measure=item.unit_of_measure.name,
        created=item.created,
        changed=item.changed,
        amount=float(amount or 0),
        location=location_orm_to_schema(item.location),
    )


def inbound_order_item_orm_to_schema(
    item: InboundOrderItem,
) -> InboundOrderItemSchema:
    return InboundOrderItemSchema(
        product=product_orm_to_schema(item.stock_product),
        amount=float(item.amount),
        unit_price=float(item.unit_price),
        changed=item.changed,
        created=item.created,
    )


def inbound_order_orm_to_schema(order: InboundOrder) -> InboundOrderSchema:
    return InboundOrderSchema(
        created=order.created,
        changed=order.changed,
        code=order.code,
        external_code=order.external_code,
        supplier=customer_orm_to_schema(order.supplier),
        description=order.description,
        note=order.note,
        currency=order.currency,
        warehouse_order=InboundWarehouseOrderBaseSchema(
            code=order.warehouse_order.code,
            order_code=order.code,
            state=InboundWarehouseOrderState(order.warehouse_order.state),
            created=order.warehouse_order.created,
            changed=order.warehouse_order.changed,
        )
        if (hasattr(order, "warehouse_order") and order.warehouse_order)
        else None,
        state=cast(InboundOrderState, order.state),
        items=[inbound_order_item_orm_to_schema(item) for item in order.items.all()],
    )


def credit_note_supplier_orm_to_schema(
    credit_note: CreditNoteToSupplier,
) -> CreditNoteSupplierSchema:
    return CreditNoteSupplierSchema(
        code=credit_note.code,
        created=credit_note.created,
        changed=credit_note.changed,
        reason=credit_note.reason,
        note=credit_note.note,
        state=CreditNoteState(credit_note.state),
        order=inbound_order_orm_to_schema(credit_note.order),
        items=[
            CreditNoteSupplierItemSchema(
                product=product_orm_to_schema(item.stock_product),
                amount=item.amount,
                unit_price=item.unit_price,
                changed=item.changed,
                created=item.created,
            )
            for item in credit_note.items.all()
        ],
    )


def warehouse_inbound_order_orm_to_schema(
    w_order: InboundWarehouseOrder,
) -> InboundWarehouseOrderSchema:
    return InboundWarehouseOrderSchema(
        code=w_order.code,
        created=w_order.created,
        changed=w_order.changed,
        items=[warehouse_item_orm_to_schema(item) for item in w_order.items.all()],
        completed_items_count=len(
            [
                item
                for item in w_order.items.order_by(
                    F("package_type").asc(nulls_first=True)
                )
                if not item.location.is_putaway
            ]
        ),
        order_code=w_order.order.code,
        order=InboundOrderBaseSchema(
            code=w_order.order.code,
            state=InboundOrderState(w_order.order.state),
            created=w_order.order.created,
            changed=w_order.order.changed,
            external_code=w_order.order.external_code,
            description=w_order.order.description,
            note=w_order.order.note,
            supplier=customer_orm_to_schema(w_order.order.supplier),
            currency=w_order.order.currency,
            warehouse_order_code=w_order.code,
        ),
        state=InboundWarehouseOrderState(w_order.state),
        credit_note=credit_note_supplier_orm_to_schema(w_order.order.credit_note)
        if getattr(w_order.order, "credit_note", None)
        else None,
    )
