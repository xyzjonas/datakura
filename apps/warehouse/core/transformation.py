from __future__ import annotations

from pathlib import Path

from django.db.models import F

from apps.warehouse.core.schemas.base import MediaFileSchema
from apps.warehouse.core.schemas.base_orders import (
    InboundWarehouseOrderBaseSchema,
    InboundOrderBaseSchema,
    OutboundWarehouseOrderBaseSchema,
    OutboundOrderBaseSchema,
    CreditNoteSupplierItemSchema,
    CreditNoteBaseSchema,
)
from apps.warehouse.core.schemas.customer import (
    CustomerSchema,
    CustomerGroupSchema,
    CustomerDiscountGroupSchema,
    ContactPersonSchema,
)
from apps.warehouse.core.schemas.orders import (
    InboundOrderSchema,
    InboundOrderItemSchema,
    OutboundOrderSchema,
    OutboundOrderItemSchema,
    OutboundOrderItemPricingDetailsSchema,
)
from apps.warehouse.core.schemas.credit_notes import CreditNoteSupplierSchema
from apps.warehouse.core.schemas.invoice import (
    InvoicePaymentMethodSchema,
    InvoiceSchema,
)
from apps.warehouse.core.schemas.group import ProductGroupSchema
from apps.warehouse.core.schemas.type import ProductTypeSchema
from apps.warehouse.core.schemas.product import (
    ProductSchema,
    DynamicProductPriceSchema,
    DynamicProductPriceCustomerSchema,
    DiscountGroupSchema,
)
from apps.warehouse.core.schemas.warehouse import (
    WarehouseItemSchema,
    PackageSchema,
    InboundWarehouseOrderSchema,
    OutboundWarehouseOrderSchema,
    WarehouseMovementSchema,
    WarehouseLocationSchema,
    WarehouseLocationDetailSchema,
    WarehouseLocationWithCountSchema,
    BatchSchema,
)
from apps.warehouse.core.schemas.barcode import BarcodeSchema
from apps.warehouse.models.barcode import Barcode
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderItem,
    InboundOrderState,
    OutboundOrder,
    OutboundOrderItem,
    OutboundOrderState,
    CreditNoteToSupplier,
    CreditNoteToCustomer,
    CreditNoteState,
    Invoice,
    InvoicePaymentMethod,
)
from apps.warehouse.models.packaging import PackageType
from apps.warehouse.models.product import (
    StockProduct,
    StockProductPrice,
    PriceGroup,
    ProductGroup,
    ProductType,
)
from apps.warehouse.models.warehouse import (
    WarehouseItem,
    WarehouseMovement,
    InboundWarehouseOrder,
    OutboundWarehouseOrder,
    WarehouseLocation,
    InboundWarehouseOrderState,
    OutboundWarehouseOrderState,
    Batch,
)


def product_group_orm_to_schema(group: ProductGroup) -> ProductGroupSchema:
    return ProductGroupSchema(
        name=group.name,
        created=group.created,
        changed=group.changed,
    )


def product_type_orm_to_schema(product_type: ProductType) -> ProductTypeSchema:
    return ProductTypeSchema(
        name=product_type.name,
        created=product_type.created,
        changed=product_type.changed,
    )


def barcode_orm_to_schema(barcode: Barcode | None = None) -> BarcodeSchema | None:
    if not barcode:
        return None
    return BarcodeSchema(
        code=barcode.code,
        barcode_type=barcode.barcode_type,
        is_primary=barcode.is_primary,
        created=barcode.created,
        changed=barcode.changed,
    )


def invoice_payment_method_orm_to_schema(
    payment_method: InvoicePaymentMethod,
) -> InvoicePaymentMethodSchema:
    return InvoicePaymentMethodSchema(
        id=payment_method.pk,
        name=payment_method.name,
        created=payment_method.created,
        changed=payment_method.changed,
    )


def invoice_document_to_schema(invoice: Invoice) -> MediaFileSchema | None:
    if not invoice.document:
        return None
    return MediaFileSchema(
        name=Path(invoice.document.name).name,
        url=invoice.document.url,
    )


def invoice_orm_to_schema(invoice: Invoice) -> InvoiceSchema:
    return InvoiceSchema(
        code=invoice.code,
        customer=customer_orm_to_schema(invoice.customer) if invoice.customer else None,
        supplier=customer_orm_to_schema(invoice.supplier) if invoice.supplier else None,
        issued_date=invoice.issued_date,
        due_date=invoice.due_date,
        payment_method=invoice_payment_method_orm_to_schema(invoice.payment_method),
        external_code=invoice.external_code,
        taxable_supply_date=invoice.taxable_supply_date,
        paid_date=invoice.paid_date,
        currency=invoice.currency,
        note=invoice.note,
        document=invoice_document_to_schema(invoice),
        created=invoice.created,
        changed=invoice.changed,
    )


def batch_orm_to_schema(batch: Batch) -> BatchSchema:
    barcode = batch.get_primary_barcode()
    return BatchSchema(
        id=batch.pk,
        primary_barcode=barcode_orm_to_schema(barcode) if barcode else None,
        created=batch.created,
        changed=batch.changed,
    )


def location_orm_to_schema(location: WarehouseLocation) -> WarehouseLocationSchema:
    return WarehouseLocationSchema(
        warehouse_name=location.warehouse.name,
        code=location.code,
        changed=location.changed,
        created=location.created,
        is_putaway=location.is_putaway,
    )


def location_orm_to_schema_with_count(
    location: WarehouseLocation,
) -> WarehouseLocationWithCountSchema:
    return WarehouseLocationWithCountSchema(
        **location_orm_to_schema(location).model_dump(),
        count=location.items.values("stock_product").distinct().count(),
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
        discount_group=CustomerDiscountGroupSchema(
            created=customer.discount_group.created,
            changed=customer.discount_group.changed,
            code=customer.discount_group.code,
            name=customer.discount_group.name,
            discount_percent=float(customer.discount_group.discount_percent),
            is_active=customer.discount_group.is_active,
        )
        if customer.discount_group
        else None,
        contacts=[
            ContactPersonSchema.from_orm(contact) for contact in customer.contacts.all()
        ],
        note=customer.note,
        register_information=customer.register_information,
    )


def product_orm_to_schema(product: StockProduct) -> ProductSchema:
    dynamic_prices = [
        dynamic_product_price_orm_to_schema(dynamic_price)
        for dynamic_price in product.dynamic_prices.all()
    ]

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
        barcodes=product.get_barcodes(),
        primary_barcode=barcode_orm_to_schema(product.get_primary_barcode()),
        dynamic_prices=dynamic_prices,
    )


def get_product_by_code(product_code: str) -> ProductSchema:
    product = StockProduct.objects.prefetch_related(
        "unit_of_measure",
        "type",
        "group",
        "dynamic_prices__customer",
    ).get(code=product_code)
    return product_orm_to_schema(product)


def dynamic_product_price_orm_to_schema(
    dynamic_price: StockProductPrice,
) -> DynamicProductPriceSchema:
    return DynamicProductPriceSchema(
        price_id=dynamic_price.pk,
        created=dynamic_price.created,
        changed=dynamic_price.changed,
        discount_percent=float(dynamic_price.discount_percent),
        customer=DynamicProductPriceCustomerSchema(
            code=dynamic_price.customer.code,
            name=dynamic_price.customer.name,
        ),
    )


def discount_group_orm_to_schema(discount_group: PriceGroup) -> DiscountGroupSchema:
    return DiscountGroupSchema(
        created=discount_group.created,
        changed=discount_group.changed,
        code=discount_group.code,
        name=discount_group.name,
        discount_percent=float(discount_group.discount_percent),
        is_active=discount_group.is_active,
    )


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

    bar = item.get_primary_barcode()
    return WarehouseItemSchema(
        id=item.pk,
        primary_barcode=bar.code if bar else None,
        product=product_orm_to_schema(item.stock_product),
        unit_of_measure=item.unit_of_measure.name,
        created=item.created,
        changed=item.changed,
        amount=float(amount or 0),
        location=location_orm_to_schema(item.location),
        inbound_order_code=item.order_in.code if item.order_in else None,
        package=package_type,
        batch=batch_orm_to_schema(item.batch) if getattr(item, "batch") else None,  # type: ignore
        tracking_level=item.tracking_level,  # type: ignore
    )


def inbound_order_item_orm_to_schema(
    item: InboundOrderItem,
) -> InboundOrderItemSchema:
    return InboundOrderItemSchema(
        product=product_orm_to_schema(item.stock_product),
        amount=float(item.amount),
        unit_price=float(item.unit_price),
        total_price=float(item.total_price),
        index=item.index,
        changed=item.changed,
        created=item.created,
    )


def outbound_order_item_orm_to_schema(
    item: OutboundOrderItem,
    pricing_details: OutboundOrderItemPricingDetailsSchema | None = None,
) -> OutboundOrderItemSchema:
    return OutboundOrderItemSchema(
        product=product_orm_to_schema(item.stock_product),
        amount=float(item.amount),
        unit_price=float(item.unit_price),
        total_price=float(item.total_price),
        index=item.index,
        pricing_details=pricing_details,
        changed=item.changed,
        created=item.created,
    )


def credit_note_supplier_orm_to_base_schema(
    credit_note: CreditNoteToSupplier | CreditNoteToCustomer,
) -> CreditNoteBaseSchema:
    return CreditNoteBaseSchema(
        code=credit_note.code,
        created=credit_note.created,
        changed=credit_note.changed,
        reason=credit_note.reason,
        note=credit_note.note,
        state=CreditNoteState.get_label(credit_note.state),
        items=[
            CreditNoteSupplierItemSchema(
                product=product_orm_to_schema(item.stock_product),
                amount=float(item.amount),
                unit_price=float(item.unit_price),
                changed=item.changed,
                created=item.created,
            )
            for item in credit_note.items.all()
        ],
    )


def inbound_warehouse_order_to_base_schema(
    w_order: InboundWarehouseOrder,
) -> InboundWarehouseOrderBaseSchema:
    def to_shallow_base(
        order: InboundWarehouseOrder,
    ) -> InboundWarehouseOrderBaseSchema:
        return InboundWarehouseOrderBaseSchema(
            code=order.code,
            order_code=order.order.code,
            state=InboundWarehouseOrderState.get_label(order.state),
            created=order.created,
            changed=order.changed,
            parent_order=None,
            child_orders=[],
        )

    parent_order = w_order.primary_order

    return InboundWarehouseOrderBaseSchema(
        code=w_order.code,
        order_code=w_order.order.code,
        state=InboundWarehouseOrderState.get_label(w_order.state),
        created=w_order.created,
        changed=w_order.changed,
        parent_order=to_shallow_base(parent_order) if parent_order else None,
        child_orders=[to_shallow_base(child) for child in w_order.derived_orders.all()],
    )


def inbound_order_orm_to_schema(order: InboundOrder) -> InboundOrderSchema:
    warehouse_orders = [
        InboundWarehouseOrderBaseSchema(
            code=wo.code,
            order_code=order.code,
            state=InboundWarehouseOrderState.get_label(wo.state),
            created=wo.created,
            changed=wo.changed,
            parent_order=(
                InboundWarehouseOrderBaseSchema(
                    code=wo.primary_order.code,
                    order_code=wo.primary_order.order.code,
                    state=InboundWarehouseOrderState.get_label(wo.primary_order.state),
                    created=wo.primary_order.created,
                    changed=wo.primary_order.changed,
                    parent_order=None,
                    child_orders=[],
                )
                if wo.primary_order
                else None
            ),
            child_orders=[
                InboundWarehouseOrderBaseSchema(
                    code=child.code,
                    order_code=child.order.code,
                    state=InboundWarehouseOrderState.get_label(child.state),
                    created=child.created,
                    changed=child.changed,
                    parent_order=None,
                    child_orders=[],
                )
                for child in wo.derived_orders.all()
            ],
        )
        for wo in order.warehouse_orders.order_by("-created").all()
    ]
    return InboundOrderSchema(
        created=order.created,
        changed=order.changed,
        code=order.code,
        external_code=order.external_code,
        supplier=customer_orm_to_schema(order.supplier),
        description=order.description,
        note=order.note,
        currency=order.currency,
        warehouse_order_codes=[wo.code for wo in order.warehouse_orders.all()],
        warehouse_orders=warehouse_orders,
        state=InboundOrderState.get_label(order.state),
        items=[inbound_order_item_orm_to_schema(item) for item in order.items.all()],
        credit_note=credit_note_supplier_orm_to_base_schema(order.credit_note)
        if getattr(order, "credit_note", None)
        else None,
        invoice=invoice_orm_to_schema(order.invoice) if order.invoice else None,
        requested_delivery_date=order.requested_delivery_date,
        cancelled_date=order.cancelled_date,
        received_date=order.received_date,
    )


def outbound_order_orm_to_schema(order: OutboundOrder) -> OutboundOrderSchema:
    def to_outbound_warehouse_base(
        warehouse_order: OutboundWarehouseOrder,
        fallback_order_code: str,
    ) -> OutboundWarehouseOrderBaseSchema:
        warehouse_order_parent = warehouse_order.order
        return OutboundWarehouseOrderBaseSchema(
            code=warehouse_order.code,
            order_code=warehouse_order_parent.code
            if warehouse_order_parent
            else fallback_order_code,
            state=OutboundWarehouseOrderState.get_label(warehouse_order.state),
            created=warehouse_order.created,
            changed=warehouse_order.changed,
            parent_order=None,
            child_orders=[],
        )

    warehouse_orders = [
        OutboundWarehouseOrderBaseSchema(
            code=wo.code,
            order_code=order.code,
            state=OutboundWarehouseOrderState.get_label(wo.state),
            created=wo.created,
            changed=wo.changed,
            parent_order=(
                to_outbound_warehouse_base(wo.primary_order, order.code)
                if wo.primary_order
                else None
            ),
            child_orders=[
                to_outbound_warehouse_base(child, order.code)
                for child in wo.derived_orders.all()
            ],
        )
        for wo in order.warehouse_orders.order_by("-created").all()
    ]
    return OutboundOrderSchema(
        created=order.created,
        changed=order.changed,
        code=order.code,
        external_code=order.external_code,
        customer=customer_orm_to_schema(order.customer),
        description=order.description,
        note=order.note,
        currency=order.currency,
        warehouse_order_codes=[wo.code for wo in order.warehouse_orders.all()],
        warehouse_orders=warehouse_orders,
        state=OutboundOrderState.get_label(order.state),
        items=[outbound_order_item_orm_to_schema(item) for item in order.items.all()],
        credit_note=credit_note_supplier_orm_to_base_schema(order.credit_note)
        if getattr(order, "credit_note", None)
        else None,
        invoice=invoice_orm_to_schema(order.invoice) if order.invoice else None,
        requested_delivery_date=order.requested_delivery_date,
        cancelled_date=order.cancelled_date,
        fulfilled_date=order.fulfilled_date,
    )


def credit_note_supplier_orm_to_schema(
    credit_note: CreditNoteToSupplier,
) -> CreditNoteSupplierSchema:
    return CreditNoteSupplierSchema(
        **credit_note_supplier_orm_to_base_schema(credit_note).model_dump(),
        order=InboundOrderBaseSchema(
            code=credit_note.order.code,
            state=InboundOrderState.get_label(credit_note.order.state),
            created=credit_note.order.created,
            changed=credit_note.order.changed,
            external_code=credit_note.order.external_code,
            description=credit_note.order.description,
            note=credit_note.order.note,
            supplier=customer_orm_to_schema(credit_note.order.supplier),
            currency=credit_note.order.currency,
            warehouse_order_codes=[
                wo.code for wo in credit_note.order.warehouse_orders.all()
            ],
            requested_delivery_date=credit_note.order.requested_delivery_date,
            cancelled_date=credit_note.order.cancelled_date,
            received_date=credit_note.order.received_date,
        ),
    )


def warehouse_inbound_order_orm_to_schema(
    w_order: InboundWarehouseOrder,
) -> InboundWarehouseOrderSchema:
    received_amount = sum(float(item.amount) for item in w_order.order.items.all())
    remaining_amount = sum(
        float(item.amount)
        for item in w_order.items.filter(location__is_putaway=True).all()
    )

    parent_order = w_order.primary_order

    return InboundWarehouseOrderSchema(
        code=w_order.code,
        created=w_order.created,
        changed=w_order.changed,
        items=[warehouse_item_orm_to_schema(item) for item in w_order.items.all()],
        movements=[
            warehouse_movement_orm_to_schema(movement)
            for movement in w_order.warehouse_movements.order_by("-moved_at")
        ],
        completed_items_count=len(
            [
                item
                for item in w_order.items.order_by(
                    F("package_type").asc(nulls_first=True)
                )
                if not item.location.is_putaway
            ]
        ),
        total_amount=received_amount,
        remaining_amount=remaining_amount,
        order_code=w_order.order.code,
        order=InboundOrderBaseSchema(
            code=w_order.order.code,
            state=InboundOrderState.get_label(w_order.order.state),
            created=w_order.order.created,
            changed=w_order.order.changed,
            external_code=w_order.order.external_code,
            description=w_order.order.description,
            note=w_order.order.note,
            supplier=customer_orm_to_schema(w_order.order.supplier),
            currency=w_order.order.currency,
            warehouse_order_codes=[
                wo.code for wo in w_order.order.warehouse_orders.all()
            ],
            requested_delivery_date=w_order.order.requested_delivery_date,
            cancelled_date=w_order.order.cancelled_date,
            received_date=w_order.order.received_date,
        ),
        state=InboundWarehouseOrderState.get_label(w_order.state),
        parent_order=(
            InboundWarehouseOrderBaseSchema(
                code=parent_order.code,
                order_code=parent_order.order.code,
                state=InboundWarehouseOrderState.get_label(parent_order.state),
                created=parent_order.created,
                changed=parent_order.changed,
                parent_order=None,
                child_orders=[],
            )
            if parent_order
            else None
        ),
        child_orders=[
            InboundWarehouseOrderBaseSchema(
                code=child.code,
                order_code=child.order.code,
                state=InboundWarehouseOrderState.get_label(child.state),
                created=child.created,
                changed=child.changed,
                parent_order=None,
                child_orders=[],
            )
            for child in w_order.derived_orders.all()
        ],
        credit_note=credit_note_supplier_orm_to_schema(w_order.order.credit_note)
        if getattr(w_order.order, "credit_note", None)
        else None,
    )


def warehouse_outbound_order_to_base_schema(
    w_order: OutboundWarehouseOrder,
) -> OutboundWarehouseOrderBaseSchema:
    linked_order = w_order.order
    if linked_order is None:
        raise ValueError(
            f"Outbound warehouse order {w_order.code} is missing linked outbound order"
        )

    def to_shallow_base(
        order: OutboundWarehouseOrder,
    ) -> OutboundWarehouseOrderBaseSchema:
        order_parent = order.order
        return OutboundWarehouseOrderBaseSchema(
            code=order.code,
            order_code=order_parent.code if order_parent else linked_order.code,
            state=OutboundWarehouseOrderState.get_label(order.state),
            created=order.created,
            changed=order.changed,
            parent_order=None,
            child_orders=[],
        )

    parent_order = w_order.primary_order
    return OutboundWarehouseOrderBaseSchema(
        code=w_order.code,
        order_code=linked_order.code,
        state=OutboundWarehouseOrderState.get_label(w_order.state),
        created=w_order.created,
        changed=w_order.changed,
        parent_order=to_shallow_base(parent_order) if parent_order else None,
        child_orders=[to_shallow_base(child) for child in w_order.derived_orders.all()],
    )


def warehouse_outbound_order_orm_to_schema(
    w_order: OutboundWarehouseOrder,
) -> OutboundWarehouseOrderSchema:
    linked_order = w_order.order
    if linked_order is None:
        raise ValueError(
            f"Outbound warehouse order {w_order.code} is missing linked outbound order"
        )

    expected_amount = sum(float(item.amount) for item in linked_order.items.all())
    moved_amount = sum(
        float(movement.amount) for movement in w_order.warehouse_movements.all()
    )
    remaining_amount = max(0.0, expected_amount - moved_amount)

    parent_order = w_order.primary_order

    return OutboundWarehouseOrderSchema(
        code=w_order.code,
        created=w_order.created,
        changed=w_order.changed,
        items=[],
        movements=[
            warehouse_movement_orm_to_schema(movement)
            for movement in w_order.warehouse_movements.order_by("-moved_at")
        ],
        completed_items_count=0,
        total_amount=expected_amount,
        remaining_amount=remaining_amount,
        order_code=linked_order.code,
        order=OutboundOrderBaseSchema(
            code=linked_order.code,
            state=OutboundOrderState.get_label(linked_order.state),
            created=linked_order.created,
            changed=linked_order.changed,
            external_code=linked_order.external_code,
            description=linked_order.description,
            note=linked_order.note,
            customer=customer_orm_to_schema(linked_order.customer),
            currency=linked_order.currency,
            warehouse_order_codes=[
                wo.code for wo in linked_order.warehouse_orders.all()
            ],
            requested_delivery_date=linked_order.requested_delivery_date,
            cancelled_date=linked_order.cancelled_date,
            fulfilled_date=linked_order.fulfilled_date,
        ),
        state=OutboundWarehouseOrderState.get_label(w_order.state),
        parent_order=(
            warehouse_outbound_order_to_base_schema(parent_order)
            if parent_order
            else None
        ),
        child_orders=[
            warehouse_outbound_order_to_base_schema(child)
            for child in w_order.derived_orders.all()
        ],
    )


def warehouse_movement_orm_to_schema(
    movement: WarehouseMovement,
) -> WarehouseMovementSchema:
    return WarehouseMovementSchema(
        moved_at=movement.moved_at,
        location_from_code=movement.location_from.code
        if movement.location_from
        else None,
        location_to_code=movement.location_to.code if movement.location_to else None,
        stock_product=product_orm_to_schema(movement.stock_product),
        amount=float(movement.amount),
        item=warehouse_item_orm_to_schema(movement.item) if movement.item else None,
        batch_id=movement.batch_id,
    )
