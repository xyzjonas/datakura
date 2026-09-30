from django.core.management.base import BaseCommand, CommandError

from apps.warehouse.core.services.data_import.errors import DataImportError
from apps.warehouse.core.services.data_import.stock_import import (
    StockImportService,
)


class Command(BaseCommand):
    help = "Import legacy warehouse stock (locations and items) from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True, help="Path to JSON")
        parser.add_argument(
            "--warehouse",
            type=str,
            required=True,
            help="Name of the target warehouse (created if missing)",
        )

    def handle(self, *args, **options):
        path = options["file"]
        self.stdout.write(f"Importing stock from: '{path}'")

        try:
            summary = StockImportService(options["warehouse"]).import_from_path(path)
        except DataImportError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Import completed: {summary.items_created} items, "
                f"{summary.locations_created} locations created, "
                f"{summary.locations_existing} locations reused"
            )
        )
