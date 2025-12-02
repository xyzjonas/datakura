from django.contrib import admin

from apps.warehouse.models.customer import ContactPerson, Customer, CustomerGroup
from apps.warehouse.models.orders import IncomingOrder, IncomingOrderItem
from apps.warehouse.models.packaging import PackageType
from apps.warehouse.models.product import (
    StockProduct,
    UnitOfMeasure,
    ProductType,
    ProductGroup,
)
from apps.warehouse.models.warehouse import (
    WarehouseItem,
    Warehouse,
    WarehouseLocation,
    WarehouseMovement,
    WarehouseOrderIn,
    WarehouseOrderOut,
)

admin.site.register(WarehouseItem)
admin.site.register(Warehouse)
admin.site.register(WarehouseLocation)
admin.site.register(PackageType)
admin.site.register(WarehouseMovement)

admin.site.register(ProductType)
admin.site.register(ProductGroup)
admin.site.register(UnitOfMeasure)

admin.site.register(ContactPerson)
admin.site.register(CustomerGroup)
admin.site.register(Customer)

admin.site.register(IncomingOrder)
admin.site.register(IncomingOrderItem)

admin.site.register(WarehouseOrderIn)
admin.site.register(WarehouseOrderOut)


@admin.register(StockProduct)
class StockProductAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
