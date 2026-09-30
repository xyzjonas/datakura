from django.core.management.base import BaseCommand, CommandError

from apps.warehouse.core.services.data_import.errors import DataImportError
from apps.warehouse.core.services.data_import.product_import import (
    ProductImportService,
)


class Command(BaseCommand):
    help = "Import legacy products from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True, help="Path to JSON")

    def handle(self, *args, **options):
        path = options["file"]
        self.stdout.write(f"Importing products from: '{path}'")

        try:
            summary = ProductImportService().import_from_path(path)
        except DataImportError as exc:
            raise CommandError(str(exc)) from exc

        for message in summary.warnings:
            self.stdout.write(self.style.WARNING(message))

        self.stdout.write(
            self.style.SUCCESS(
                f"Import completed: {summary.created_count} created, "
                f"{summary.updated_count} updated, {summary.skipped_count} skipped, "
                f"{summary.barcodes_attached} barcodes"
            )
        )
