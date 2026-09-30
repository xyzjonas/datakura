"""Import of legacy products (product + stock product + prices + barcodes) from JSON"""

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.warehouse.core.services.data_import.common import (
    parse_rows,
    read_text,
    validate_rows,
)
from apps.warehouse.core.services.data_import.errors import DataImportError
from apps.warehouse.core.services.data_import.progress import ImportProgress
from apps.warehouse.models.barcode import Barcode, BarcodeType
from apps.warehouse.models.currency import CURRENCY_CHOICES
from apps.warehouse.models.packaging import UnitOfMeasure
from apps.warehouse.models.product import ProductGroup, ProductType, StockProduct

TYPE_MAP = {"GOODS": "Zboží"}
PROGRESS_EVERY = 1000
DEFAULT_CURRENCY = "CZK"
DEFAULT_UOM = "KS"
BASE_PRICE_TYPE = "NORMAL"
_CURRENCIES = {code for code, _ in CURRENCY_CHOICES}
_MULTI_PACK_UOM = re.compile(r"^(\d+)\s*([A-Za-z]+)$")
_MAX_2DP = Decimal(10) ** 8


def _blank_to_none(value: Any) -> Any:
    return None if isinstance(value, str) and not value.strip() else value


def _to_2dp(value: Decimal) -> Decimal:
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if abs(rounded) >= _MAX_2DP:
        raise ValueError(f"Value {value} does not fit into 10 digits / 2 decimals")
    return rounded


class LegacyMeta(BaseModel):
    code: str = Field(..., alias="Code", min_length=1)
    value: str = Field("", alias="Value")

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    @field_validator("value", mode="before")
    @classmethod
    def none_to_empty(cls, value):
        return "" if value is None else value


class LegacyPrice(BaseModel):
    price_type: str | None = Field(None, alias="ProductPriceTypeCode")
    price: Decimal = Field(..., alias="Price", ge=0)
    currency: str | None = Field(None, alias="CurrencyCode")
    uom: str | None = Field(None, alias="UnitTypeCode")
    unit_count: Decimal = Field(Decimal(1), alias="UnitCount", gt=0)
    quantity_min: Decimal | None = Field(None, alias="QuantityMin")
    quantity_max: Decimal | None = Field(None, alias="QuantityMax")
    customer_id: int | None = Field(None, alias="CustomerId")

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    @field_validator("currency", "uom", mode="before")
    @classmethod
    def blank(cls, value):
        return _blank_to_none(value)

    @field_validator("unit_count", mode="before")
    @classmethod
    def none_to_one(cls, value):
        return 1 if _blank_to_none(value) is None else value

    @field_validator("currency")
    @classmethod
    def known_currency(cls, value):
        if value is not None and value not in _CURRENCIES:
            raise ValueError(f"Unknown currency '{value}'")
        return value

    @property
    def is_generic(self) -> bool:
        """Price valid for everybody and any quantity"""
        return (
            self.customer_id is None
            and self.quantity_min is None
            and self.quantity_max is None
        )


class LegacyBarcode(BaseModel):
    code: str = Field(..., alias="BarCode", min_length=1, max_length=100)
    amount: Decimal | None = Field(None, alias="Amount")

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)


class LegacyStockProduct(BaseModel):
    code: str = Field(..., alias="Code", min_length=1, max_length=255)
    name: str | None = Field(None, alias="Name", max_length=255)
    weight: Decimal | None = Field(None, alias="Weight", ge=0)
    barcodes: list[LegacyBarcode] = Field(default_factory=list, alias="StockBarCodes")

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    @field_validator("name", mode="before")
    @classmethod
    def blank(cls, value):
        return _blank_to_none(value)

    @field_validator("barcodes", mode="before")
    @classmethod
    def drop_blank_barcodes(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return [
            b
            for b in value
            if not (isinstance(b, dict) and _blank_to_none(b.get("BarCode")) is None)
        ]


class LegacyProduct(BaseModel):
    code: str = Field(..., alias="Code", min_length=1, max_length=255)
    name: str = Field(..., alias="Name", min_length=1, max_length=255)
    buy_price: Decimal = Field(Decimal(0), alias="BuyPrice")
    type_code: str = Field(..., alias="ProductTypeCode", min_length=1)
    group_code: str | None = Field(None, alias="ProductGroupCode")
    uom: str | None = Field(None, alias="UnitTypeCode")
    metas: list[LegacyMeta] = Field(default_factory=list, alias="ProductMetas")
    prices: list[LegacyPrice] = Field(default_factory=list, alias="ProductPrices")
    stock_product: LegacyStockProduct | None = Field(None, alias="StockProduct")

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    @field_validator("group_code", "uom", mode="before")
    @classmethod
    def blank(cls, value):
        return _blank_to_none(value)

    @field_validator("buy_price", mode="before")
    @classmethod
    def none_to_zero(cls, value):
        return 0 if value is None else value

    @field_validator("metas", "prices", mode="before")
    @classmethod
    def none_to_list(cls, value):
        return [] if value is None else value

    @field_validator("type_code")
    @classmethod
    def map_type(cls, value):
        return TYPE_MAP.get(value, value)


@dataclass
class ProductImportSummary:
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    barcodes_attached: int = 0
    warnings: list[str] = field(default_factory=list)


class ProductImportService:
    def import_from_path(
        self, path: str | Path, progress: ImportProgress | None = None
    ) -> ProductImportSummary:
        logger.info("Product import: reading '{}'", path)
        return self.import_from_json(read_text(path), progress)

    def import_from_json(
        self, raw: str, progress: ImportProgress | None = None
    ) -> ProductImportSummary:
        progress = progress or ImportProgress()
        rows = parse_rows(raw)
        logger.info("Product import: parsed {} records", len(rows))
        progress.set_phase("validating")
        validated = validate_rows(LegacyProduct, rows)
        progress.set_total(len(validated))
        return self._import_products(validated, progress)

    @transaction.atomic
    def _import_products(
        self, products: list[tuple[int, LegacyProduct]], progress: ImportProgress
    ) -> ProductImportSummary:
        summary = ProductImportSummary()
        errors: list[str] = []
        total = len(products)

        for position, (index, product) in enumerate(products, start=1):
            progress.advance()
            if position % PROGRESS_EVERY == 0:
                logger.info("Product import: processed {}/{} records", position, total)

            if product.stock_product is None:
                logger.debug("Product '{}': no stock product, skipped", product.code)
                summary.skipped_count += 1
                summary.warnings.append(
                    f"Product '{product.code}': no stock product, skipped"
                )
                continue

            try:
                with transaction.atomic():
                    created = self._import_product(product, summary)
            except Exception as exc:
                logger.error(
                    "Product '{}' failed: {}: {}",
                    product.code,
                    type(exc).__name__,
                    exc,
                )
                errors.append(f"Product #{index} '{product.code}': {exc}")
                continue

            logger.debug(
                "Product '{}': {}", product.code, "created" if created else "updated"
            )
            if created:
                summary.created_count += 1
            else:
                summary.updated_count += 1

        if errors:
            logger.error(
                "Product import failed, rolling back: {} failing records", len(errors)
            )
            raise DataImportError("\n".join(errors))

        for warning in summary.warnings:
            logger.warning("Product import: {}", warning)
        logger.info(
            "Product import done: {} created, {} updated, {} skipped, "
            "{} barcodes, {} warnings",
            summary.created_count,
            summary.updated_count,
            summary.skipped_count,
            summary.barcodes_attached,
            len(summary.warnings),
        )
        return summary

    def _import_product(
        self, product: LegacyProduct, summary: ProductImportSummary
    ) -> bool:
        stock = product.stock_product
        assert stock is not None
        if stock.code != product.code:
            raise ValueError(f"StockProduct code '{stock.code}' != product code")

        product_type, _ = ProductType.objects.get_or_create(name=product.type_code)
        group = None
        if product.group_code:
            group, _ = ProductGroup.objects.get_or_create(name=product.group_code)
        uom_name = product.uom or DEFAULT_UOM
        uom = self._get_or_create_uom(uom_name)

        base_price, currency = self._base_price(product, uom_name, summary)
        defaults: dict[str, Any] = {
            "name": stock.name or product.name,
            "type": product_type,
            "group": group,
            "unit_of_measure": uom,
            "unit_weight": _to_2dp(stock.weight or Decimal(0)),
            "purchase_price": _to_2dp(product.buy_price),
            "base_price": base_price,
            "attributes": {meta.code: meta.value for meta in product.metas},
        }
        if currency:
            defaults["currency"] = currency

        stock_product, created = StockProduct.objects.update_or_create(
            code=stock.code, defaults=defaults
        )
        self._attach_barcodes(stock_product, stock, summary)
        return created

    @staticmethod
    def _get_or_create_uom(name: str) -> UnitOfMeasure:
        """'100KS' -> UoM '100KS' worth 100 of base UoM 'KS'"""
        if name.lower() in (DEFAULT_UOM.lower(), f"100{DEFAULT_UOM}".lower()):
            name = name.upper()

        match = _MULTI_PACK_UOM.match(name)
        if not match:
            return UnitOfMeasure.objects.get_or_create(name=name)[0]

        base_name = match.group(2).upper()
        base, _ = UnitOfMeasure.objects.get_or_create(name=base_name)
        uom, _ = UnitOfMeasure.objects.get_or_create(
            name=name,
            defaults={"base_uom": base, "amount_of_base_uom": Decimal(match.group(1))},
        )
        return uom

    @staticmethod
    def _base_price(
        product: LegacyProduct, uom_name: str, summary: ProductImportSummary
    ) -> tuple[Decimal, str | None]:
        """Generic NORMAL price expressed per single product UoM"""
        candidates = [
            p
            for p in product.prices
            if p.price_type == BASE_PRICE_TYPE and p.is_generic
        ]
        for price in candidates:
            if (price.uom or uom_name) != uom_name:
                summary.warnings.append(
                    f"Product '{product.code}': price in '{price.uom}' "
                    f"differs from product UoM '{uom_name}', ignored"
                )
                continue
            return _to_2dp(price.price / price.unit_count), price.currency
        return Decimal(0), None

    @staticmethod
    def _attach_barcodes(
        stock_product: StockProduct,
        stock: LegacyStockProduct,
        summary: ProductImportSummary,
    ) -> None:
        has_primary = stock_product.get_primary_barcode() is not None
        for barcode in stock.barcodes:
            if barcode.amount is not None:
                summary.warnings.append(
                    f"Product '{stock.code}': barcode '{barcode.code}' amount "
                    f"{barcode.amount} dropped (unsupported)"
                )

            owned_elsewhere = (
                Barcode.objects.filter(code=barcode.code)
                .exclude(**_owner(stock_product))
                .exists()
            )
            if owned_elsewhere:
                summary.warnings.append(
                    f"Product '{stock.code}': barcode '{barcode.code}' already "
                    "belongs to another product, skipped"
                )
                continue

            stock_product.attach_barcode(
                barcode.code, _barcode_type(barcode.code), is_primary=not has_primary
            )
            has_primary = True
            summary.barcodes_attached += 1


def _owner(obj) -> dict[str, Any]:
    return {
        "content_type": ContentType.objects.get_for_model(obj),
        "object_id": obj.pk,
    }


def _barcode_type(code: str) -> BarcodeType:
    if code.isdigit():
        return {13: BarcodeType.EAN13, 8: BarcodeType.EAN8, 12: BarcodeType.UPC}.get(
            len(code), BarcodeType.CUSTOM
        )
    return BarcodeType.CUSTOM
