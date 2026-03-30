"""Utility command to seed the database with test data"""

from pathlib import Path

from django.core.management.base import BaseCommand
from apps.warehouse.core.services.product_import import ProductCsvImportService


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

        service = ProductCsvImportService()
        summary = service.import_from_path(path)

        for message in summary.errors:
            self.stdout.write(self.style.WARNING(message))

        self.stdout.write(
            self.style.SUCCESS(
                f"Import completed: {summary.created_count} created, "
                f"{summary.updated_count} updated, {summary.skipped_count} skipped"
            )
        )
