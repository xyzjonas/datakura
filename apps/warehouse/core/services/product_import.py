import csv
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

from django.db import transaction
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from apps.warehouse.models.packaging import UnitOfMeasure
from apps.warehouse.models.product import ProductGroup, ProductType, StockProduct

TYPE_MAP = {"GOODS": "Zboží"}


class ProductRow(BaseModel):
    code: str = Field(..., alias="Kód", description="Product code")
    name: str = Field(..., alias="Jméno", description="Product name")
    loc_product_type_code: str = Field(..., alias="locProductTypeCode")
    loc_product_group_code: str = Field(..., alias="locProductGroupCode")
    base_price: str | None = Field(None, alias="locBasePrice")
    currency: str | None = Field(None, alias="locCurrencyCode")
    purchase_price: float | None = Field(
        None, alias="Nákupní cena", description="Purchase price"
    )
    uom: str | None = Field(..., alias="locUnitTypeCode", description="Unit of measure")
    weight: float | None = Field(None, alias="Hmotnost", description="Weight")
    loc_width: float | None = Field(0, alias="locWidth")
    loc_height: float | None = Field(0, alias="locHeight")
    loc_depth: float | None = Field(0, alias="locDepth")
    loc_part_number: str | None = Field(None, alias="locPartNumber")
    loc_customs_declaration_group: str | None = Field(
        None, alias="locCustomsDeclarationGroup"
    )
    attributes: dict[str, str] = Field(alias="locProductMetas", default_factory=dict)
    note: str | None = Field(None, alias="Poznámka", description="Note")

    @field_validator(
        "base_price",
        "purchase_price",
        "weight",
        "loc_width",
        "loc_height",
        "loc_depth",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, value):
        if value == "" or value is None:
            return None
        return value

    @field_validator("loc_product_type_code", mode="before")
    @classmethod
    def map_type(cls, value):
        return TYPE_MAP.get(value, value)

    @field_validator("uom", mode="before")
    @classmethod
    def uppercase_certain_uoms(cls, value):
        if value == "" or value is None:
            return None

        if value in ("100KS", "100ks", "ks", "KS", "Ks", "kS"):
            return value.upper()

        return value

    @field_validator("attributes", mode="before")
    @classmethod
    def parse_attrs(cls, value: str):
        if value == "" or value is None:
            return {}

        value = value.replace(
            "DIN:_931,_ISO:_4014,_ČSN:_021103.55:DIN: 931, ISO: 4014, ČSN: 021103.55",
            "DIN: 931, ISO: 4014, ČSN: 021103.55",
        )

        result = {}
        items = value.split(",")
        if len(items) == 1:
            items = value.split(";")

        for item_pair in items:
            split_items = item_pair.split(":", maxsplit=2)
            if len(split_items) == 1:
                result[split_items[0].strip()] = ""
            else:
                key, val = split_items
                result[key.strip()] = val.strip()

        return result

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        frozen=True,
    )


@dataclass
class ProductImportSummary:
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    errors: list[str] = field(default_factory=list)


class ProductCsvImportService:
    def __init__(self, delimiter: str = "&"):
        self.delimiter = delimiter

    def import_from_path(
        self, path: str | Path, encoding: str = "utf-8-sig"
    ) -> ProductImportSummary:
        with open(path, "r", encoding=encoding) as csvfile:
            return self.import_from_file_obj(csvfile)

    def import_from_uploaded_file(self, uploaded_file) -> ProductImportSummary:
        content = uploaded_file.read().decode("utf-8-sig")
        return self.import_from_file_obj(StringIO(content))

    def import_from_file_obj(self, csv_file) -> ProductImportSummary:
        reader = csv.DictReader(csv_file, delimiter=self.delimiter)
        summary = ProductImportSummary()

        for index, row in enumerate(reader):
            row_number = index + 2

            try:
                product = ProductRow(**row)  # type: ignore
            except ValidationError as exc:
                summary.skipped_count += 1
                summary.errors.append(f"Row {row_number}: {exc}")
                continue

            try:
                result = self._import_product(product)
            except Exception as exc:
                summary.skipped_count += 1
                summary.errors.append(f"Row {row_number}: {exc}")
                continue

            if result == "created":
                summary.created_count += 1
            elif result == "updated":
                summary.updated_count += 1
            else:
                summary.skipped_count += 1

        return summary

    @transaction.atomic
    def _import_product(self, product: ProductRow) -> str:
        product_type, _ = ProductType.objects.get_or_create(
            name=product.loc_product_type_code
        )

        product_group = None
        if product.loc_product_group_code:
            product_group, _ = ProductGroup.objects.get_or_create(
                name=product.loc_product_group_code
            )

        product_uom, _ = UnitOfMeasure.objects.get_or_create(name=product.uom or "KS")

        _, created = StockProduct.objects.update_or_create(
            code=product.code,
            defaults={
                "name": product.name,
                "type": product_type,
                "group": product_group,
                "unit_of_measure": product_uom,
                "unit_weight": product.weight or 0,
                "currency": product.currency or "CZK",
                "purchase_price": product.purchase_price or 0,
                "base_price": product.base_price or 0,
                "attributes": product.attributes,
                "customs_declaration_group": product.loc_customs_declaration_group,
            },
        )

        return "created" if created else "updated"
