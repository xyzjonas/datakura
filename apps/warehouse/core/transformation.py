from __future__ import annotations

from apps.warehouse.api.schemas.customer import (
    CustomerSchema,
    CustomerGroupSchema,
    ContactPersonSchema,
)
from apps.warehouse.api.schemas.product import ProductSchema
from apps.warehouse.api.schemas.warehouse import (
    WarehouseItemSchema,
    StockItemSchema,
    PackageSchema,
)
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.packaging import Package
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import WarehouseItem


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
    )


def get_product_by_code(product_code: str) -> ProductSchema:
    product = StockProduct.objects.prefetch_related(
        "unit_of_measure", "type", "group"
    ).get(code=product_code)
    return product_orm_to_schema(product)


def package_orm_to_schema(package: Package | None) -> PackageSchema | None:
    if package is None:
        return None
    return PackageSchema(
        changed=package.changed,
        created=package.created,
        code=package.code,
        unit=package.type.unit_of_measure.name,
        type=package.type.name,
        description=package.type.description,
        amount=float(package.type.amount),
    )


def warehouse_item_orm_to_schema(item: WarehouseItem) -> WarehouseItemSchema:
    amount = float(item.amount) if item.amount else None
    package = package_orm_to_schema(item.package)
    if package and item.package_amount_in_product_uom:
        package.amount = item.package_amount_in_product_uom
        if amount is None:
            amount = package.amount

    return WarehouseItemSchema(
        code=package.code if package else item.code,
        package=package,
        stock_item=StockItemSchema(
            code=item.stock_product.code,
            name=item.stock_product.name,
            created=item.stock_product.created,
            changed=item.stock_product.changed,
        ),
        unit_of_measure=item.unit_of_measure.name,
        created=item.created,
        changed=item.changed,
        amount=float(amount or 0),
    )
