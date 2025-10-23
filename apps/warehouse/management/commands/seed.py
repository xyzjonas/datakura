"""Utility command to seed the database with test data"""

import random

from django.core.management.base import BaseCommand

from apps.warehouse.models.warehouse import (
    WarehouseLocation,
    Warehouse,
    WarehouseItem,
    PackageType,
)
from apps.warehouse.models.stock import StockItem


class Command(BaseCommand):
    help = "Seed with test data"

    def handle(self, *args, **options):
        self.stdout.write("Creating warehouses...")
        warehouses = []
        for warehouse_name in ["Centrála"] + [
            f"Sklad-{x}" for x in ["A", "B", "C", "D"]
        ]:
            warehouse, _ = Warehouse.objects.get_or_create(name=warehouse_name)
            warehouses.append(warehouse)

        self.stdout.write("Creating warehouse locations...")
        locations = []
        for warehouse in warehouses:
            # Each warehouse has multiple sections and rows
            for section in ["A", "B", "C", "D", "E", "F"]:
                for row in range(1, 4):  # 3 rows per section
                    for shelf in range(1, 6):  # 5 shelves per row
                        code = f"{warehouse.name}-{section}{row:02d}-{shelf}"
                        location, _ = WarehouseLocation.objects.get_or_create(
                            code=code, warehouse=warehouse
                        )
                        locations.append(location)

        self.stdout.write(f"Created {len(locations)} locations")

        self.stdout.write("Creating package types...")
        package_types = []
        package_specs = [
            ("Krabice 100ks", 100),
            ("Krabice 200ks", 200),
            ("Krabice 500ks", 500),
            ("Krabice 1000ks", 1000),
            ("Balení 25ks", 25),
            ("Balení 50ks", 50),
            ("Volné kusy", 1),
            ("Paleta 5000ks", 5000),
            ("Paleta 10000ks", 10000),
            ("Box 250ks", 250),
        ]

        for name, count in package_specs:
            pkg, _ = PackageType.objects.get_or_create(
                name=name, defaults={"count": count}
            )
            package_types.append(pkg)

        self.stdout.write("Creating stock items...")
        stock_items = []

        # Vruty (screws)
        vrut_types = [
            ("dřevo 6H A4", "571-4100"),
            ("dřevo 6H Zn", "571-4200"),
            ("uni ZH TX část. z. A4", "7505H-4100"),
            ("uni ZH TX část. z. Zn", "7505H-4200"),
            ("terasa TX A4", "571-5100"),
            ("sádrokarton TX", "571-6100"),
            ("universální TX", "571-7100"),
            ("konstrukční TX", "571-8100"),
        ]

        sizes = [
            "05x040",
            "05x050",
            "05x060",
            "05x070",
            "05x080",
            "06x050",
            "06x060",
            "06x070",
            "06x080",
            "06x100",
            "08x060",
            "08x080",
            "08x100",
            "08x120",
            "08x140",
            "10x080",
            "10x100",
            "10x120",
            "10x140",
            "10x160",
            "12x100",
            "12x120",
            "12x140",
            "12x150",
            "12x160",
        ]

        for vrut_type, code_base in vrut_types:
            for size in sizes:
                name = f"Vrut {vrut_type} {size}"
                code = f"{code_base}-{size}"
                item, _ = StockItem.objects.get_or_create(
                    code=code, defaults={"name": name}
                )
                stock_items.append(item)

        # Úhelníky (angle brackets)
        uhelnik_types = [
            (
                "ÚP4",
                "MT6104",
                [
                    "20x20x37x1mm",
                    "21x21x50x1mm",
                    "21x21x67x1mm",
                    "21x21x86x1mm",
                    "90x37x39x2mm",
                ],
            ),
            ("ÚP5", "MT6105", ["30x30x30x2mm", "48x48x40x2mm"]),
            ("ÚP5P", "MT6105P", ["48x48x40x2,5mm"]),
            ("ÚP6", "MT6106", ["25x25x15x2mm", "40x40x15x2mm"]),
            (
                "ÚP7",
                "MT6107B",
                [
                    "60x60x45x2mm",
                    "70x70x55x2mm",
                    "90x90x65x2mm",
                    "90x90x65x2,5mm",
                    "100x100x90x3mm",
                ],
            ),
            ("UP10", "MT6110", ["90x90x65x1,5mm"]),
        ]

        for utype, code_base, dimensions in uhelnik_types:
            for dim in dimensions:
                name = f"Úhelník {utype}, {dim} Zn"
                code = f"{code_base}-{dim.split('x')[0]}"
                item, _ = StockItem.objects.get_or_create(
                    code=code, defaults={"name": name}
                )
                stock_items.append(item)

        # Závlačky (cotter pins)
        zavlacka_sizes = [
            "06x050",
            "06x060",
            "06x080",
            "08x050",
            "08x063",
            "08x080",
            "08x090",
            "08x100",
            "08x112",
            "10x063",
            "10x080",
            "10x100",
            "10x125",
        ]

        for size in zavlacka_sizes:
            name = f"Závlačka ZB {size}"
            code = f"94-1801-{size}"
            item, _ = StockItem.objects.get_or_create(
                code=code, defaults={"name": name}
            )
            stock_items.append(item)

        # Hmoždinky (dowels)
        hmozdinka_types = [
            ("nylon UX", "555-1100"),
            ("rámová RMX", "555-2100"),
            ("ocelová SX", "555-3100"),
            ("rychlomontážní KPX", "555-4100"),
        ]

        hmozdinka_sizes = [
            "06x30",
            "06x50",
            "08x50",
            "08x60",
            "10x60",
            "10x80",
            "12x70",
            "12x100",
        ]

        for htype, code_base in hmozdinka_types:
            for size in hmozdinka_sizes:
                name = f"Hmoždinka {htype} {size}"
                code = f"{code_base}-{size}"
                item, _ = StockItem.objects.get_or_create(
                    code=code, defaults={"name": name}
                )
                stock_items.append(item)

        # Matice (nuts)
        matice_types = [
            ("šestihranná DIN 934 Zn", "431-1000"),
            ("šestihranná DIN 934 A4", "431-1100"),
            ("samojistná DIN 985 Zn", "431-2000"),
            ("křídlová DIN 315 Zn", "431-3000"),
        ]

        matice_sizes = ["M4", "M5", "M6", "M8", "M10", "M12", "M14", "M16"]

        for mtype, code_base in matice_types:
            for size in matice_sizes:
                name = f"Matice {mtype} {size}"
                code = f"{code_base}-{size}"
                item, _ = StockItem.objects.get_or_create(
                    code=code, defaults={"name": name}
                )
                stock_items.append(item)

        # Podložky (washers)
        podlozka_types = [
            ("plochá DIN 125 Zn", "410-1000"),
            ("plochá DIN 125 A4", "410-1100"),
            ("pružná DIN 127 Zn", "410-2000"),
            ("stavěcí DIN 988 Zn", "410-3000"),
        ]

        for ptype, code_base in podlozka_types:
            name = f"Podložka {ptype} {size}"
            code = f"{code_base}-{size}"
            item, _ = StockItem.objects.get_or_create(
                code=code, defaults={"name": name}
            )
            stock_items.append(item)

        # Šrouby (bolts)
        sroub_types = [
            ("metrický se šestihranem DIN 933 Zn", "301-1000"),
            ("metrický se šestihranem DIN 933 A4", "301-1100"),
            ("se zápustnou hlavou DIN 965 Zn", "302-1000"),
            ("s čočkovou hlavou DIN 7985 Zn", "303-1000"),
        ]

        sroub_sizes = [
            "M4x20",
            "M4x30",
            "M5x20",
            "M5x30",
            "M5x40",
            "M6x20",
            "M6x30",
            "M6x40",
            "M6x50",
            "M8x20",
            "M8x30",
            "M8x40",
            "M8x50",
            "M8x60",
            "M10x30",
            "M10x40",
            "M10x50",
            "M10x60",
            "M10x80",
        ]

        for stype, code_base in sroub_types:
            for size in sroub_sizes:
                name = f"Šroub {stype} {size}"
                code = f"{code_base}-{size}"
                item, _ = StockItem.objects.get_or_create(
                    code=code, defaults={"name": name}
                )
                stock_items.append(item)

        # Hřebíky (nails)
        hrebik_types = [
            ("stavební hladký", "201-1000"),
            ("stavební rýhovaný", "201-2000"),
            ("pro příčné palubky", "201-3000"),
            ("bezhlavý", "201-4000"),
        ]

        hrebik_sizes = [
            "25x2,0",
            "30x2,5",
            "40x2,8",
            "50x3,0",
            "60x3,4",
            "70x3,4",
            "80x3,8",
            "100x4,2",
        ]

        for htype, code_base in hrebik_types:
            for size in hrebik_sizes:
                name = f"Hřebík {htype} {size}mm"
                code = f"{code_base}-{size.replace(',', '')}"
                item, _ = StockItem.objects.get_or_create(
                    code=code, defaults={"name": name}
                )
                stock_items.append(item)

        self.stdout.write(f"Created {len(stock_items)} stock items")

        self.stdout.write("Creating warehouse items (this may take a while)...")
        warehouse_items_created = 0
        batch_size = 500
        items_to_create = []

        for _ in range(55000):  # Create 55k items
            stock_item = random.choice(stock_items)
            package_type = random.choice(package_types)
            location = random.choice(locations)

            # Remaining units: random but logical based on package size
            max_remaining = package_type.count
            if random.choice([True, True, True, False]):
                remaining = max_remaining
            else:
                remaining = random.randint(0, max_remaining)

            item = WarehouseItem(
                stock_item=stock_item,
                package_type=package_type,
                remaining=remaining,
                warehouse_location=location,
            )
            items_to_create.append(item)

            if len(items_to_create) >= batch_size:
                WarehouseItem.objects.bulk_create(
                    items_to_create, ignore_conflicts=True
                )
                warehouse_items_created += len(items_to_create)
                items_to_create = []
                self.stdout.write(
                    f"Created {warehouse_items_created} warehouse items..."
                )

        # Create remaining items
        if items_to_create:
            WarehouseItem.objects.bulk_create(items_to_create, ignore_conflicts=True)
            warehouse_items_created += len(items_to_create)

        self.stdout.write(self.style.SUCCESS("Successfully seeded database!"))
        self.stdout.write(f"  - Warehouses: {len(warehouses)}")
        self.stdout.write(f"  - Locations: {len(locations)}")
        self.stdout.write(f"  - Package types: {len(package_types)}")
        self.stdout.write(f"  - Stock items: {len(stock_items)}")
        self.stdout.write(f"  - Warehouse items: {warehouse_items_created}")
