from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.warehouse.core.exceptions import WarehouseGenericError
from apps.warehouse.core.schemas.product import (
    ProductBarcodeCreateSchema,
    ProductCreateOrUpdateSchema,
    ProductDuplicateSchema,
    DynamicProductPriceCreateSchema,
    DynamicProductPriceUpdateSchema,
)
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.core.transformation import get_product_by_code
from apps.warehouse.models.barcode import BarcodeType
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.packaging import UnitOfMeasure
from apps.warehouse.models.product import (
    StockProduct,
    DynamicPriceType,
    PriceGroup,
    ProductType,
    ProductGroup,
    StockProductPrice,
)


class StockProductsService:
    @staticmethod
    def _build_product_defaults(params: ProductCreateOrUpdateSchema):
        product_type, _ = ProductType.objects.get_or_create(name=params.type)
        unit_of_measure, _ = UnitOfMeasure.objects.get_or_create(name=params.unit)
        product_group = None
        if params.group and params.group.strip():
            product_group, _ = ProductGroup.objects.get_or_create(name=params.group)

        return {
            "name": params.name,
            "type": product_type,
            "group": product_group,
            "unit_of_measure": unit_of_measure,
            "unit_weight": Decimal(str(params.unit_weight or 0)),
            "currency": params.currency,
            "purchase_price": Decimal(str(params.purchase_price or 0)),
            "base_price": Decimal(str(params.base_price or 0)),
            "customs_declaration_group": params.customs_declaration_group,
            "attributes": params.attributes,
        }

    @staticmethod
    @transaction.atomic
    def create_product(params: ProductCreateOrUpdateSchema):
        defaults = StockProductsService._build_product_defaults(params)
        product = StockProduct.objects.create(code=params.code, **defaults)
        audit_service.add_entry(
            product,
            action=AuditAction.CREATE,
            reason=AuditMessages.PRODUCT_CREATED.CS,
        )
        return get_product_by_code(product.code)

    @staticmethod
    @transaction.atomic
    def update_product(product_code: str, params: ProductCreateOrUpdateSchema):
        product = StockProduct.objects.get(code=product_code)
        previous = get_product_by_code(product_code)

        product.code = params.code
        defaults = StockProductsService._build_product_defaults(params)
        for field, value in defaults.items():
            setattr(product, field, value)
        product.save()

        current = get_product_by_code(product.code)
        changes: dict[str, dict[str, str]] = {}
        prev_dump = previous.model_dump()
        curr_dump = current.model_dump()
        for key, old_value in prev_dump.items():
            if key in (
                "created",
                "changed",
                "barcodes",
                "primary_barcode",
                "dynamic_prices",
            ):
                continue
            if old_value != curr_dump.get(key):
                changes[key] = {
                    "old": str(old_value),
                    "new": str(curr_dump.get(key)),
                }

        audit_service.add_entry(
            product,
            action=AuditAction.UPDATE,
            reason=AuditMessages.PRODUCT_UPDATED.CS,
            changes=changes,
        )

        return current

    @staticmethod
    @transaction.atomic
    def duplicate_product(product_code: str, params: ProductDuplicateSchema):
        if params.code == product_code:
            raise WarehouseGenericError(
                "Duplicated product code must be different from source product code"
            )

        StockProduct.objects.get(code=product_code)
        return StockProductsService.create_product(
            ProductCreateOrUpdateSchema(**params.model_dump())
        )

    @staticmethod
    def _validate_discount(discount_percent: Decimal) -> None:
        if discount_percent < 0 or discount_percent > 100:
            raise WarehouseGenericError("discount_percent must be between 0 and 100")

    @staticmethod
    def _resolve_price_target(
        price_type: str,
        group_name: str | None,
        customer_code: str | None,
    ) -> tuple[PriceGroup | None, Customer | None]:
        if price_type == DynamicPriceType.GROUP_DISCOUNT:
            if not group_name:
                raise WarehouseGenericError("group_name is required for GROUP_DISCOUNT")
            if customer_code:
                raise WarehouseGenericError(
                    "customer_code must not be set for GROUP_DISCOUNT"
                )
            group, _ = PriceGroup.objects.get_or_create(name=group_name)
            return group, None

        if price_type == DynamicPriceType.CUSTOMER_DISCOUNT:
            if not customer_code:
                raise WarehouseGenericError(
                    "customer_code is required for CUSTOMER_DISCOUNT"
                )
            if group_name:
                raise WarehouseGenericError(
                    "group_name must not be set for CUSTOMER_DISCOUNT"
                )
            customer = Customer.objects.get(code=customer_code)
            return None, customer

        raise WarehouseGenericError(
            "price_type must be one of GROUP_DISCOUNT or CUSTOMER_DISCOUNT"
        )

    @staticmethod
    @transaction.atomic
    def add_dynamic_price(
        product_code: str,
        params: DynamicProductPriceCreateSchema,
    ):
        product = StockProduct.objects.get(code=product_code)
        price_type = DynamicPriceType(params.price_type)
        discount_percent = Decimal(str(params.discount_percent))
        StockProductsService._validate_discount(discount_percent)
        group, customer = StockProductsService._resolve_price_target(
            price_type=price_type,
            group_name=params.group_name,
            customer_code=params.customer_code,
        )

        try:
            StockProductPrice.objects.create(
                product=product,
                price_type=price_type,
                discount_percent=discount_percent,
                group=group,
                customer=customer,
            )
        except IntegrityError as exc:
            raise WarehouseGenericError(str(exc))

        return get_product_by_code(product_code)

    @staticmethod
    @transaction.atomic
    def update_dynamic_price(
        product_code: str,
        price_id: int,
        params: DynamicProductPriceUpdateSchema,
    ):
        price = StockProductPrice.objects.select_related("product").get(
            pk=price_id,
            product__code=product_code,
        )

        next_price_type = DynamicPriceType(params.price_type or price.price_type)
        next_discount = Decimal(str(params.discount_percent or price.discount_percent))
        StockProductsService._validate_discount(next_discount)

        next_group_name = params.group_name
        next_customer_code = params.customer_code
        if params.price_type is None:
            next_group_name = (
                next_group_name
                if next_group_name is not None
                else (price.group.name if price.group else None)
            )
            next_customer_code = (
                next_customer_code
                if next_customer_code is not None
                else (price.customer.code if price.customer else None)
            )

        group, customer = StockProductsService._resolve_price_target(
            price_type=next_price_type,
            group_name=next_group_name,
            customer_code=next_customer_code,
        )

        try:
            price.price_type = next_price_type
            price.discount_percent = next_discount
            price.group = group
            price.customer = customer
            price.save()
        except IntegrityError as exc:
            raise WarehouseGenericError(str(exc))

        return get_product_by_code(product_code)

    @staticmethod
    @transaction.atomic
    def delete_dynamic_price(product_code: str, price_id: int):
        price = StockProductPrice.objects.select_related("product").get(
            pk=price_id,
            product__code=product_code,
        )
        price.delete()
        return get_product_by_code(product_code)

    @staticmethod
    def add_barcode(product_code: str, params: ProductBarcodeCreateSchema):
        product = StockProduct.objects.get(code=product_code)

        try:
            product.attach_barcode(
                code=params.code,
                barcode_type=BarcodeType(params.barcode_type),
                is_primary=params.is_primary,
            )
        except ValueError as exc:
            raise WarehouseGenericError(str(exc))

        return get_product_by_code(product_code)


stock_product_service = StockProductsService()
