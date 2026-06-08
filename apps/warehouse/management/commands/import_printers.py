from django.core.management.base import BaseCommand

from apps.warehouse.models.printer import Printer


class Command(BaseCommand):
    help = "Import printers from legacy user settings data"

    def handle(self, *args, **options):
        """
        Import printers based on unique IP addresses from the legacy data.
        Uses IP as the code (name) and leaves description empty.
        """
        printers_data = [
            {"ip": "10.0.0.70", "dpi": 300, "port": 9100},
            {"ip": "10.0.0.71", "dpi": 300, "port": 9100},
            {"ip": "10.0.0.72", "dpi": 203, "port": 9100},
        ]

        created_count = 0
        updated_count = 0

        for printer_data in printers_data:
            ip = printer_data["ip"]
            dpi = printer_data["dpi"]
            port = printer_data["port"]

            printer, created = Printer.objects.update_or_create(
                code=ip,
                defaults={
                    "ip": ip,
                    "dpi": dpi,
                    "port": port,
                    "description": None,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created printer: {ip} (DPI: {dpi})")
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"Updated printer: {ip} (DPI: {dpi})")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nImport complete: {created_count} created, {updated_count} updated"
            )
        )
