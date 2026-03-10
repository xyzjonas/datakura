from django.contrib import admin

from apps.warehouse.models.customer import ContactPerson, Customer, CustomerGroup
from apps.warehouse.models.orders import InboundOrder, InboundOrderItem
from apps.warehouse.models.packaging import PackageType
from apps.warehouse.models.product import (
    StockProduct,
    UnitOfMeasure,
    ProductType,
    ProductGroup,
    PriceGroup,
    StockProductPrice,
)
from apps.warehouse.models.warehouse import (
    WarehouseItem,
    Warehouse,
    WarehouseLocation,
    WarehouseMovement,
    InboundWarehouseOrder,
    OutboundWarehouseOrder,
    Batch,
)
from apps.warehouse.models.barcode import Barcode


@admin.register(WarehouseItem)
class WarehouseItemAdmin(admin.ModelAdmin):
    autocomplete_fields = ["stock_product", "location", "batch"]

    # Standard optimizations
    list_display = ["id", "stock_product", "tracking_level"]
    list_filter = ["tracking_level"]  # Be careful with filters on huge sets!
    search_fields = ["id"]


@admin.register(Barcode)
class BarcodeAdmin(admin.ModelAdmin):
    pass


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    search_fields = ["code"]


admin.site.register(Warehouse)


@admin.register(WarehouseLocation)
class WarehouseLocationAdmin(admin.ModelAdmin):
    search_fields = ["code"]


admin.site.register(PackageType)
admin.site.register(WarehouseMovement)

admin.site.register(ProductType)
admin.site.register(ProductGroup)
admin.site.register(UnitOfMeasure)


@admin.register(PriceGroup)
class PriceGroupAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(StockProductPrice)
class StockProductPriceAdmin(admin.ModelAdmin):
    autocomplete_fields = ["product", "group", "customer"]
    list_display = [
        "id",
        "product",
        "price_type",
        "discount_percent",
        "group",
        "customer",
    ]


admin.site.register(ContactPerson)
admin.site.register(CustomerGroup)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    search_fields = ("code", "name")


admin.site.register(InboundOrder)
admin.site.register(InboundOrderItem)


@admin.register(InboundWarehouseOrder)
class InboundWarehouseOrderAdmin(admin.ModelAdmin):
    search_fields = ["code"]


admin.site.register(OutboundWarehouseOrder)


@admin.register(StockProduct)
class StockProductAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
