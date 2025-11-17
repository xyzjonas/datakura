"""Utility command to seed the database with test data"""

import random
from string import ascii_letters

from django.core.management.base import BaseCommand

from apps.warehouse.models.packaging import UnitOfMeasure
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
        _100ks = UnitOfMeasure.objects.get(name="100KS")
        _ks = UnitOfMeasure.objects.get(name="KS")
        products = [
            ("Závlačka ZB 08,0x090", "94-1801-08-090", _100ks.pk),
            ("Šr 6H límec hl. 8,8 ZB M08x012", "6921-0801-08-012", _100ks.pk),
            ('Objímka dvoušroubová M8/M10 72–78 2 1/2"', "S312007278", _100ks.pk),
            ("Podl SCHNORR S M10/10,5x16x1", "S20010-1800-10", _100ks.pk),
            ("Šr TEX PH límec D+ ZB 04,2x016", "7504FL-1801-4,2-016", _100ks.pk),
            ("Matice nýt mikro ZH 6H ZB M06(1,0-3,5)", "S10056-1801-06-3,5", _100ks.pk),
            ("Šr TEX PH D+ A2 04,8x019", "7504N-2200-4,8-019", _100ks.pk),
            ("FIS EM PLUS 390 S 390 ml", "FR544176", _ks.pk),
            ("SDS Plus II 16/250/310", "FR531829", _ks.pk),
            ("SXRL 10X80 FUS", "FR522719", _100ks.pk),
            ("SXRL 8X80 T", "FR540114", _100ks.pk),
            ("SXRL 8X120 T", "FR540116", _100ks.pk),
            ("SXRL 8X80 FUS", "FR540129", _100ks.pk),
            ("SXRL 8X100 FUS", "FR540130", _100ks.pk),
            ("SXRL 8X120 FUS", "FR540131", _100ks.pk),
            ("SXRL 10X120 FUS", "FR522721", _100ks.pk),
            ("SXRL 10X80 FUS", "FR522719", _100ks.pk),
            ("SDS Plus II 6,0/50/110", "FR531765", _ks.pk),
            ("HSS-R 2,5x30x57", "FR543088", _ks.pk),
            ("HSS-R 4,2x43x75", "FR543105", _ks.pk),
            ("HSS-R 4,5x47x80", "FR543108", _ks.pk),
            ("HSS-R 5,0x52x86", "FR543113", _ks.pk),
            ("HSS-R 8,0x75x117", "FR543143", _ks.pk),
            ("HSS-R 8,5x75x117", "FR543148", _ks.pk),
            ("DUOPOWER 12x60 DIY", "FR538253", _100ks.pk),
            ("Matice samojistná A2 M03", "985-2200-03", _100ks.pk),
            ("Matice nízká A2 M12", "439-2200-012", _100ks.pk),
            ("Matice nízká | 4 | ZB M16x1,5", "439-0401-016-1,5", _100ks.pk),
            ("Kolík válcový 08,0 m6x020", "7A-1800-08-020", _100ks.pk),
            ("Matice vys. 6H 1,5D s nákr. | 10 | M16", "6331-1000-16", _100ks.pk),
            ("Šr 6H 8.8 HDG M24x070", "933-0804-24-070", _100ks.pk),
            ("Pero těsné 06x06x080", "6885A-1800-06-080", _100ks.pk),
            ("Kolík válcový A1 08,0 m6x040", "7A-2100-08-040", _100ks.pk),
            ("Vrut SDK COARSE 03,5x035", "18182E-1806-03,5-035", _100ks.pk),
            ("Šr VH IMB 8.8 ZB M36x130", "912-0801-36-130", _100ks.pk),
            ("Šroub závitotvorný PH D+ ZB M05x016", "7500C-1801-05-016", _100ks.pk),
        ]
        for name, code, uom_id in products:
            StockProduct.objects.get_or_create(
                code=code,
                defaults={"name": name, "unit_of_measure_id": uom_id, "type_id": 1},
            )
