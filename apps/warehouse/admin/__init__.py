from django.contrib import admin
from apps.warehouse.models.stock import StockItem
from apps.warehouse.models.warehouse import (
    WarehouseItem,
    Warehouse,
    WarehouseLocation,
    PackageType,
)

admin.site.register(StockItem)
admin.site.register(WarehouseItem)
admin.site.register(Warehouse)
admin.site.register(WarehouseLocation)
admin.site.register(PackageType)
