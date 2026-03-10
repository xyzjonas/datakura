from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.warehouse.core.exceptions import WarehouseGenericError
from apps.warehouse.core.schemas.product import (
    ProductBarcodeCreateSchema,
    DynamicProductPriceCreateSchema,
    DynamicProductPriceUpdateSchema,
)
from apps.warehouse.core.transformation import get_product_by_code
from apps.warehouse.models.barcode import BarcodeType
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.product import (
    StockProduct,
    DynamicPriceType,
    PriceGroup,
    StockProductPrice,
)


class StockProductsService:
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
