from __future__ import annotations

from apps.warehouse.core.exceptions import WarehouseGenericError
from apps.warehouse.core.schemas.product import ProductBarcodeCreateSchema
from apps.warehouse.core.transformation import get_product_by_code
from apps.warehouse.models.barcode import BarcodeType
from apps.warehouse.models.product import StockProduct


class StockProductsService:
    @staticmethod
    def update_pricing(product_code: str) -> None:
        pass

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
