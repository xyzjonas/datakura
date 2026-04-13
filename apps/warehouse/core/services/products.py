from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import IntegrityError, transaction

from apps.warehouse.core.exceptions import WarehouseGenericError
from apps.warehouse.core.schemas.product import (
    ProductBarcodeCreateSchema,
    ProductCreateOrUpdateSchema,
    ProductDuplicateSchema,
    CustomerPriceOverrideUpsertSchema,
    DynamicProductPriceCreateSchema,
    DynamicProductPriceUpdateSchema,
    SellingPriceLookupSchema,
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
    PriceGroup,
    ProductType,
    ProductGroup,
    StockProductPrice,
)


class StockProductsService:
    @staticmethod
    def _derive_discount_percent(base_price: Decimal, final_price: Decimal) -> Decimal:
        if base_price <= 0:
            return Decimal("0")
        return ((Decimal("1") - final_price / base_price) * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @staticmethod
    def _resolve_selling_price(
        product: StockProduct,
        customer: Customer | None = None,
    ) -> tuple[Decimal, Decimal, str, str]:
        base_price = Decimal(str(product.base_price or 0))

        if customer:
            customer_discount = StockProductPrice.objects.filter(
                product=product,
                customer=customer,
            ).first()
            if customer_discount:
                final_price = Decimal(str(customer_discount.fixed_price))
                discount_percent = StockProductsService._derive_discount_percent(
                    base_price,
                    final_price,
                )
                return (
                    final_price,
                    discount_percent,
                    f"Customer override for {customer.code}",
                    "CUSTOMER_OVERRIDE",
                )

            if customer.discount_group and customer.discount_group.is_active:
                discount_percent = Decimal(
                    str(customer.discount_group.discount_percent)
                )
                final_price = base_price * (
                    Decimal("1") - discount_percent / Decimal("100")
                )
                return (
                    final_price,
                    discount_percent,
                    f"Discount group {customer.discount_group.code}",
                    "CUSTOMER_GROUP",
                )

        return base_price, Decimal("0"), "Base selling price", "BASE_PRICE"

    @staticmethod
    def get_selling_price_lookup(
        product_code: str,
        customer_code: str | None = None,
    ) -> SellingPriceLookupSchema:
        product = StockProduct.objects.get(code=product_code)
        customer = Customer.objects.get(code=customer_code) if customer_code else None
        base_price = Decimal(str(product.base_price or 0))

        final_price, discount_percent, reason, source = (
            StockProductsService._resolve_selling_price(product, customer)
        )
        return SellingPriceLookupSchema(
            product_code=product.code,
            customer_code=customer.code if customer else None,
            base_price=float(base_price.quantize(Decimal("0.01"))),
            final_price=float(final_price.quantize(Decimal("0.01"))),
            discount_percent=float(discount_percent),
            reason=reason,
            source=source,
        )

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
    def _validate_fixed_price(fixed_price: Decimal) -> None:
        if fixed_price < 0:
            raise WarehouseGenericError(
                "fixed_price must be greater than or equal to 0"
            )

    @staticmethod
    def _resolve_override_customer(customer_code: str | None) -> Customer:
        if not customer_code:
            raise WarehouseGenericError("customer_code is required")
        return Customer.objects.get(code=customer_code)

    @staticmethod
    @transaction.atomic
    def upsert_customer_price_override(
        product_code: str,
        params: CustomerPriceOverrideUpsertSchema,
    ) -> SellingPriceLookupSchema:
        product = StockProduct.objects.get(code=product_code)
        customer = StockProductsService._resolve_override_customer(params.customer_code)
        fixed_price = Decimal(str(params.fixed_price))
        StockProductsService._validate_fixed_price(fixed_price)

        StockProductPrice.objects.update_or_create(
            product=product,
            customer=customer,
            defaults={"fixed_price": fixed_price},
        )

        return StockProductsService.get_selling_price_lookup(
            product_code=product_code,
            customer_code=customer.code,
        )

    @staticmethod
    @transaction.atomic
    def add_dynamic_price(
        product_code: str,
        params: DynamicProductPriceCreateSchema,
    ):
        product = StockProduct.objects.get(code=product_code)
        fixed_price = Decimal(str(params.fixed_price))
        StockProductsService._validate_fixed_price(fixed_price)
        customer = StockProductsService._resolve_override_customer(params.customer_code)

        try:
            StockProductPrice.objects.create(
                product=product,
                fixed_price=fixed_price,
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

        next_fixed_price = Decimal(
            str(
                params.fixed_price
                if params.fixed_price is not None
                else price.fixed_price
            )
        )
        StockProductsService._validate_fixed_price(next_fixed_price)

        customer = (
            StockProductsService._resolve_override_customer(params.customer_code)
            if params.customer_code
            else price.customer
        )

        try:
            price.fixed_price = next_fixed_price
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
    def list_discount_groups() -> list[PriceGroup]:
        return list(PriceGroup.objects.order_by("code"))

    @staticmethod
    @transaction.atomic
    def create_discount_group(
        group_code: str,
        name: str,
        discount_percent: float,
        is_active: bool,
    ) -> PriceGroup:
        if not group_code or not group_code.strip():
            raise WarehouseGenericError("group_code is required")

        percent = Decimal(str(discount_percent))
        StockProductsService._validate_discount(percent)

        return PriceGroup.objects.create(
            code=group_code.strip(),
            name=name,
            discount_percent=percent,
            is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update_discount_group(
        group_code: str,
        name: str | None = None,
        discount_percent: float | None = None,
        is_active: bool | None = None,
    ) -> PriceGroup:
        group = PriceGroup.objects.get(code=group_code)

        if name is not None:
            group.name = name
        if discount_percent is not None:
            percent = Decimal(str(discount_percent))
            StockProductsService._validate_discount(percent)
            group.discount_percent = percent
        if is_active is not None:
            group.is_active = is_active

        group.save()
        return group

    @staticmethod
    @transaction.atomic
    def delete_discount_group(group_code: str) -> None:
        PriceGroup.objects.get(code=group_code).delete()

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
