from apps.warehouse.models.packaging import PackageType
from apps.warehouse.models.product import StockProduct


def get_package_amount_in_product_uom(
    package_type: PackageType, stock_product: StockProduct
) -> float | None:
    """
    Get amounts in the common unit (product unit).

    I.e.: how units of a stock product can fit inside the given package

    (!) UOMs must be the same or share the same parent, otherwise the conversion isn't valid
    """
    product_uom = stock_product.unit_of_measure
    package_uom = package_type.unit_of_measure

    if not package_uom:
        return None

    if product_uom.name == package_uom.name:
        return float(package_type.amount)

    if product_uom.base_uom and product_uom.base_uom.name == package_uom.name:
        if product_uom.amount_of_base_uom is not None:
            return float(package_type.amount / product_uom.amount_of_base_uom)

    if package_uom.base_uom and package_uom.base_uom.name == product_uom.name:
        if package_uom.amount_of_base_uom is not None:
            return float(package_type.amount * package_uom.amount_of_base_uom)

    return None
