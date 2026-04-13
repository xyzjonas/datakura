from django import forms
from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from apps.warehouse.core.services.product_import import ProductCsvImportService
from apps.warehouse.models.customer import ContactPerson, Customer, CustomerGroup
from apps.warehouse.models.orders import (
    InboundOrder,
    InboundOrderItem,
    OutboundOrder,
    OutboundOrderItem,
    Invoice,
    InvoicePaymentMethod,
)
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


class StockProductImportCsvForm(forms.Form):
    csv_file = forms.FileField(label="CSV file")


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
    search_fields = ("code", "name")
    list_display = ["code", "name", "discount_percent", "is_active"]


@admin.register(StockProductPrice)
class StockProductPriceAdmin(admin.ModelAdmin):
    autocomplete_fields = ["product", "customer"]
    list_display = [
        "id",
        "product",
        "fixed_price",
        "customer",
    ]


admin.site.register(ContactPerson)
admin.site.register(CustomerGroup)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    search_fields = ("code", "name")


admin.site.register(InboundOrder)
admin.site.register(InboundOrderItem)
admin.site.register(OutboundOrder)
admin.site.register(OutboundOrderItem)
admin.site.register(Invoice)
admin.site.register(InvoicePaymentMethod)


@admin.register(InboundWarehouseOrder)
class InboundWarehouseOrderAdmin(admin.ModelAdmin):
    search_fields = ["code"]


admin.site.register(OutboundWarehouseOrder)


@admin.register(StockProduct)
class StockProductAdmin(admin.ModelAdmin):
    search_fields = ("name", "code")
    change_list_template = "admin/warehouse/stockproduct/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="warehouse_stockproduct_import_csv",
            )
        ]
        return custom_urls + urls

    def import_csv_view(self, request: HttpRequest) -> HttpResponse:
        if not self.has_change_permission(request):
            raise PermissionDenied

        if request.method == "POST":
            form = StockProductImportCsvForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data["csv_file"]
                summary = ProductCsvImportService().import_from_uploaded_file(csv_file)

                if summary.errors:
                    self.message_user(
                        request,
                        "Import completed with warnings."
                        f" {summary.created_count} created, "
                        f"{summary.updated_count} updated, {summary.skipped_count} skipped.",
                        level=messages.WARNING,
                    )
                    for error in summary.errors[:10]:
                        self.message_user(request, error, level=messages.ERROR)
                    if len(summary.errors) > 10:
                        self.message_user(
                            request,
                            f"... and {len(summary.errors) - 10} more errors.",
                            level=messages.ERROR,
                        )
                else:
                    self.message_user(
                        request,
                        f"Import completed: {summary.created_count} created, "
                        f"{summary.updated_count} updated, {summary.skipped_count} skipped.",
                        level=messages.SUCCESS,
                    )

                return HttpResponseRedirect(
                    reverse("admin:warehouse_stockproduct_changelist")
                )
        else:
            form = StockProductImportCsvForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Import products from CSV",
            "form": form,
        }
        return TemplateResponse(
            request,
            "admin/warehouse/stockproduct/import_csv.html",
            context,
        )
