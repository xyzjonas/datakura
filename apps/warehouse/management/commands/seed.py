"""Utility command to seed the database with test data"""

import random
from string import ascii_letters

from django.core.management.base import BaseCommand

from apps.warehouse.models.warehouse import (
    WarehouseLocation,
    Warehouse,
)
from apps.warehouse.models.product import (
    ProductType,
    StockProduct,
)


from apps.warehouse.tests.factories.customer import CustomerFactoryWithContacts
from apps.warehouse.tests.factories.units import create_all_uoms
from apps.warehouse.tests.factories.packaging import create_all_package_types


class Command(BaseCommand):
    help = "Seed with test data"

    def handle(self, *args, **options):
        self.stdout.write("Creating product types...")
        product_type_names = {
            "Physical Item": "Zboží",
            "Service": "Služba",
            "Assembly/Kit": "Sestava/Sada",
            "Raw Material": "Surovina",
            "Finished Good": "Hotový výrobek",
        }
        product_types = []
        for _, czech_name in product_type_names.items():
            product_type, _ = ProductType.objects.get_or_create(name=czech_name)
            product_types.append(product_type)

        self.stdout.write("Creating UoMs...")
        create_all_uoms()

        self.stdout.write("Creating package types...")
        create_all_package_types()

        self.stdout.write("Creating warehouses...")
        warehouse_codes = {"Centrála": ["A", "B"], "Pekárna": ["P"], "Nosek": ["N"]}
        warehouses = []
        for warehouse_name in warehouse_codes:
            warehouse, _ = Warehouse.objects.get_or_create(name=warehouse_name)
            warehouses.append(warehouse)

        self.stdout.write("Creating warehouse locations...")
        locations = []
        for warehouse, sections in zip(warehouses, warehouse_codes.values()):
            # Each warehouse has multiple sections and rows
            for section in sections:
                for sub_section in ascii_letters[:-15]:
                    for row in range(1, random.choice([1, 1, 1, 1, 2, 2, 3, 4, 5, 6])):
                        for shelf in range(
                            1, random.choice([1, 1, 1, 2, 2, 3, 4, 5, 6, 7, 8])
                        ):
                            code = (
                                f"{section}{sub_section.upper()}-{row:02d}-{shelf:02d}"
                            )
                            location, _ = WarehouseLocation.objects.get_or_create(
                                code=code, warehouse=warehouse
                            )
                            locations.append(location)

        self.stdout.write("Creating customers...")
        for code in ("ABA", "BCA", "CQR", "POODR"):
            CustomerFactoryWithContacts(code=code)

        # StockProductFactory.create_batch(10000)
        # self.stdout.write("Created 10000 products")

        self.stdout.write("Creating products...")
        products = [
            {
                "model": "warehouse.stockproduct",
                "pk": 1,
                "fields": {
                    "created": "2025-10-25T18:21:02.629Z",
                    "changed": "2025-10-28T12:52:56.445Z",
                    "name": "Závlačka ZB 08,0x090",
                    "code": "94-1801-08-090",
                    "type_id": 1,
                    "group_id": None,
                    "unit_of_measure_id": 3,
                },
            },
            {
                "model": "warehouse.stockproduct",
                "pk": 2,
                "fields": {
                    "created": "2025-10-28T19:52:14.479Z",
                    "changed": "2025-10-28T19:52:14.479Z",
                    "name": "Šr 6H límec hl. 8,8 ZB M08x012",
                    "code": "6921-0801-08-012",
                    "type_id": 1,
                    "group_id": None,
                    "unit_of_measure_id": 3,
                },
            },
            {
                "model": "warehouse.stockproduct",
                "pk": 3,
                "fields": {
                    "created": "2025-10-28T19:53:51.770Z",
                    "changed": "2025-10-28T19:53:51.770Z",
                    "name": 'Objímka dvoušroubová M8/M10 72–78 2 1/2"',
                    "code": "S312007278",
                    "type_id": 1,
                    "group_id": None,
                    "unit_of_measure_id": 3,
                },
            },
        ]
        for product in products:
            fields = product["fields"]
            StockProduct.objects.get_or_create(code=fields["code"], defaults=fields)
