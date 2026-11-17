from __future__ import annotations

from django.db import IntegrityError, transaction

from apps.warehouse.core.exceptions import (
    WarehouseGenericError,
    WarehouseItemBadRequestError,
)
from apps.warehouse.models.customer import Customer
from apps.warehouse.models.orders import OutboundCalculation, OutboundOrder
from apps.warehouse.models.product import CustomerProductCode, StockProduct


class CustomerProductCodesService:
    """Codes under which a customer knows our stock products."""

    @staticmethod
    def list_for_product(product_code: str) -> list[CustomerProductCode]:
        product = StockProduct.objects.get(code=product_code)
        return list(
            CustomerProductCode.objects.filter(product=product)
            .select_related("customer")
            .order_by("customer__name", "customer__code")
        )

    @staticmethod
    @transaction.atomic
    def upsert(
        product: StockProduct, customer: Customer, code: str
    ) -> CustomerProductCode:
        """Set the customer's code of the product (a product has one per customer)."""
        entry, _ = CustomerProductCode.objects.update_or_create(
            product=product, customer=customer, defaults={"code": code}
        )
        return entry

    @classmethod
    def upsert_if_given(
        cls, product: StockProduct, customer: Customer, code: str | None
    ) -> None:
        """A code given with an order/calculation item becomes the customer's code."""
        code = (code or "").strip()
        if code:
            cls.upsert(product, customer, code)

    @classmethod
    def upsert_by_codes(
        cls, product_code: str, customer_code: str, code: str
    ) -> CustomerProductCode:
        product = StockProduct.objects.get(code=product_code)
        customer = Customer.objects.get(code=customer_code)
        try:
            return cls.upsert(product, customer, code)
        except IntegrityError as exc:
            raise WarehouseGenericError(str(exc))

    @staticmethod
    @transaction.atomic
    def update(product_code: str, entry_id: int, code: str) -> CustomerProductCode:
        entry = CustomerProductCode.objects.select_related("customer").get(
            pk=entry_id, product__code=product_code
        )
        entry.code = code
        entry.save()
        return entry

    @staticmethod
    def delete(product_code: str, entry_id: int) -> None:
        CustomerProductCode.objects.get(
            pk=entry_id, product__code=product_code
        ).delete()

    @staticmethod
    def assert_order_items_have_codes(
        order: OutboundOrder | OutboundCalculation,
    ) -> None:
        """
        Customers that order by their own codes need one for every item - raises a
        bad request listing the products still lacking it.
        """
        customer = order.customer
        if not customer.requires_own_codes:
            return
        products = {
            item.stock_product_id: item.stock_product.code
            for item in order.items.select_related("stock_product")
        }
        have = CustomerProductCode.codes_for(customer, products)
        missing = [code for pk, code in products.items() if pk not in have]
        if missing:
            raise WarehouseItemBadRequestError(
                f"Customer '{customer.code}' requires own product codes, missing for: "
                f"{', '.join(sorted(missing))}"
            )


customer_product_codes_service = CustomerProductCodesService()
