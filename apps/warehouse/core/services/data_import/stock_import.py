"""Import of legacy warehouse stock (locations + stock items) from raw JSON"""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from django.db import transaction
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from apps.warehouse.core.services.data_import.errors import DataImportError
from apps.warehouse.core.services.data_import.progress import ImportProgress
from apps.warehouse.models.product import StockProduct
from apps.warehouse.models.warehouse import (
    TrackingLevel,
    Warehouse,
    WarehouseItem,
    WarehouseLocation,
)

# Legacy stock is plain quantity of a product; barcodes live on the product itself
IMPORT_TRACKING_LEVEL = TrackingLevel.FUNGIBLE
WAREHOUSE_NAME_MAX_LENGTH = 50


class LegacyStockItem(BaseModel):
    product_code: str = Field(..., alias="StockProductCode", min_length=1)
    # Legacy "Price" is deliberately ignored
    amount: Decimal = Field(..., alias="Value", ge=0, max_digits=10, decimal_places=4)

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)


class LegacyPlace(BaseModel):
    # "Name" carries stray BOMs in legacy data, "Code" is the reliable identifier
    code: str = Field(..., alias="Code", min_length=1, max_length=50)
    items: list[LegacyStockItem] = Field(default_factory=list, alias="StockItems")

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)


class LegacyWarehouse(BaseModel):
    places: list[LegacyPlace] = Field(..., alias="WarehousePlaces")

    model_config = ConfigDict(populate_by_name=True)


# Legacy warehouse object(s) or a bare list of places
_Payload = LegacyWarehouse | list[LegacyWarehouse] | list[LegacyPlace]
_PAYLOAD_ADAPTER: TypeAdapter[_Payload] = TypeAdapter(_Payload)


@dataclass
class StockImportSummary:
    locations_created: int = 0
    locations_existing: int = 0
    items_created: int = 0
    warehouse_created: bool = False


class StockImportService:
    def __init__(self, warehouse_name: str):
        self.warehouse_name = warehouse_name.strip()
        if not self.warehouse_name:
            raise DataImportError("Warehouse name must not be empty")
        if len(self.warehouse_name) > WAREHOUSE_NAME_MAX_LENGTH:
            raise DataImportError(
                f"Warehouse name too long (max {WAREHOUSE_NAME_MAX_LENGTH})"
            )

    def import_from_path(
        self, path: str | Path, progress: ImportProgress | None = None
    ) -> StockImportSummary:
        logger.info("Stock import: reading '{}'", path)
        try:
            raw = Path(path).read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise DataImportError(f"Cannot read '{path}': {exc}") from exc
        return self.import_from_json(raw, progress)

    def import_from_json(
        self, raw: str, progress: ImportProgress | None = None
    ) -> StockImportSummary:
        progress = progress or ImportProgress()
        progress.set_phase("validating")
        try:
            payload = _PAYLOAD_ADAPTER.validate_json(raw)
        except ValidationError as exc:
            raise DataImportError(f"Invalid input data: {exc}") from exc

        places: list[LegacyPlace] = []
        for source in payload if isinstance(payload, list) else [payload]:
            if isinstance(source, LegacyPlace):
                places.append(source)
            else:
                places.extend(source.places)
        logger.info(
            "Stock import [{}]: parsed {} places with {} items",
            self.warehouse_name,
            len(places),
            sum(len(place.items) for place in places),
        )
        progress.set_total(sum(len(place.items) for place in places))
        return self._import_places(places, progress)

    @transaction.atomic
    def _import_places(
        self, places: list[LegacyPlace], progress: ImportProgress
    ) -> StockImportSummary:
        products = self._resolve_products(places)
        summary = StockImportSummary()

        warehouse, summary.warehouse_created = Warehouse.objects.get_or_create(
            name=self.warehouse_name
        )

        for place in places:
            location, created = WarehouseLocation.objects.get_or_create(
                code=place.code, defaults={"warehouse": warehouse}
            )
            if not created and location.warehouse_id != warehouse.pk:
                logger.error(
                    "Stock import: location '{}' belongs to warehouse '{}'",
                    place.code,
                    location.warehouse.name,
                )
                raise DataImportError(
                    f"Location '{place.code}' already belongs to warehouse "
                    f"'{location.warehouse.name}'"
                )
            if created:
                summary.locations_created += 1
            else:
                summary.locations_existing += 1

            WarehouseItem.objects.bulk_create(
                WarehouseItem(
                    stock_product=products[item.product_code],
                    tracking_level=IMPORT_TRACKING_LEVEL,
                    amount=item.amount,
                    location=location,
                )
                for item in place.items
            )
            summary.items_created += len(place.items)
            progress.advance(len(place.items))
            logger.debug(
                "Location '{}' ({}): {} items",
                place.code,
                "created" if created else "reused",
                len(place.items),
            )

        logger.info(
            "Stock import [{}] done: warehouse {}, {} locations created, "
            "{} reused, {} items",
            self.warehouse_name,
            "created" if summary.warehouse_created else "reused",
            summary.locations_created,
            summary.locations_existing,
            summary.items_created,
        )

        return summary

    @staticmethod
    def _resolve_products(places: list[LegacyPlace]) -> dict[str, StockProduct]:
        codes = {item.product_code for place in places for item in place.items}
        products = {p.code: p for p in StockProduct.objects.filter(code__in=codes)}

        missing = sorted(codes - products.keys())
        if missing:
            logger.error(
                "Stock import: {} unknown stock products, e.g. {}",
                len(missing),
                missing[:10],
            )
            raise DataImportError(f"Stock products do not exist: {', '.join(missing)}")
        return products
