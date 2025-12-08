"""Utility command to seed the database with test data"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from pydantic import Field, BaseModel, field_validator, ConfigDict

from apps.warehouse.models.packaging import UnitOfMeasure
from apps.warehouse.models.product import StockProduct, ProductType, ProductGroup

TYPE_MAP = {"GOODS": "Zboží"}


class ProductRow(BaseModel):
    """Pydantic model for product CSV row."""

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
    def empty_str_to_none(cls, v):
        """Convert empty strings to None for decimal fields."""
        if v == "" or v is None:
            return None
        return v

    @field_validator("loc_product_type_code", mode="before")
    @classmethod
    def map_type(cls, v):
        """Convert to our standard."""
        return TYPE_MAP.get(v, v)

    @field_validator("uom", mode="before")
    @classmethod
    def uppercase_certain_uoms(cls, v):
        """Convert to our standard."""
        if v == "" or v is None:
            return None

        if v in ("100KS", "100ks", "ks", "KS", "Ks", "kS"):
            return v.upper()

        return v

    @field_validator("attributes", mode="before")
    @classmethod
    def parse_attrs(cls, v: str):
        """Convert to dicts - comma separated"""
        if v == "" or v is None:
            return {}

        v = v.replace(
            "DIN:_931,_ISO:_4014,_ČSN:_021103.55:DIN: 931, ISO: 4014, ČSN: 021103.55",
            "DIN: 931, ISO: 4014, ČSN: 021103.55",
        )

        result = {}
        items = v.split(",")
        if len(items) == 1:
            items = v.split(";")

        for item_pair in items:
            split_items = item_pair.split(":", maxsplit=2)
            if len(split_items) == 1:
                result[split_items[0].strip()] = ""
            else:
                key, value = split_items
                result[key.strip()] = value.strip()

        return result

    model_config = ConfigDict(
        populate_by_name=True,  # Allow both alias and field name
        str_strip_whitespace=True,  # Strip whitespace from strings
        validate_assignment=True,  # Validate on assignment
        arbitrary_types_allowed=True,  # Allow arbitrary types
        frozen=True,  # Make model immutable
    )


class Command(BaseCommand):
    help = "Import product data from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", type=str, help="Path to the CSV file", default="data/products.csv"
        )

    def handle(self, *args, **options):
        path = options["file"]
        self.stdout.write(f"Importing products from: '{path}'")

        if not Path(path).exists():
            self.stdout.write(self.style.ERROR(f"File not found: {path}"))
            return

        with open(path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile, delimiter="&")

            created_count = 0
            updated_count = 0
            skipped_count = 0
            for index, row in enumerate(reader):
                # try:
                product = ProductRow(**row)
                # except ValidationError as e:
                #     self.stdout.write(
                #         self.style.WARNING(
                #             f"Row: {index + 1}: Error importing product {product.code}: {str(e)}"
                #         )
                #     )

                result = self._import_product(product)
                if result == "created":
                    created_count += 1
                elif result == "updated":
                    updated_count += 1
                else:
                    skipped_count += 1
                self.stdout.write(f"{index + 1} line processed: {result}")

            self.stdout.write(
                self.style.SUCCESS(
                    f"Import completed: {created_count} created, "
                    f"{updated_count} updated, {skipped_count} skipped"
                )
            )

    @transaction.atomic
    def _import_product(self, product: ProductRow):
        """Import a single product from CSV row"""
        product_type, _ = ProductType.objects.get_or_create(
            name=TYPE_MAP.get(
                product.loc_product_type_code, product.loc_product_type_code
            )
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
