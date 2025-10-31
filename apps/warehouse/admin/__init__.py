from django.contrib import admin
from apps.warehouse.models.product import (
    StockProduct,
    UnitOfMeasureConversionFactor,
    UnitOfMeasure,
    ProductType,
    ProductGroup,
)
from apps.warehouse.models.warehouse import (
    WarehouseItem,
    Warehouse,
    WarehouseLocation,
    PackageType,
    WarehouseMovement,
)
from apps.warehouse.models.customer import ContactPerson, Customer, CustomerGroup

admin.site.register(WarehouseItem)
admin.site.register(Warehouse)
admin.site.register(WarehouseLocation)
admin.site.register(PackageType)
admin.site.register(WarehouseMovement)

admin.site.register(StockProduct)
admin.site.register(ProductType)
admin.site.register(ProductGroup)
admin.site.register(UnitOfMeasure)
admin.site.register(UnitOfMeasureConversionFactor)

admin.site.register(ContactPerson)
admin.site.register(CustomerGroup)
admin.site.register(Customer)
