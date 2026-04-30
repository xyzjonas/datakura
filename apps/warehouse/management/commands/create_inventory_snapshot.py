from django.core.management.base import BaseCommand, CommandError

from apps.warehouse.core.exceptions import WarehouseGenericError
from apps.warehouse.core.services.inventory_snapshots import inventory_snapshot_service
from apps.warehouse.models.warehouse import InventorySnapshotTriggerSource


class Command(BaseCommand):
    help = "Create an immutable inventory snapshot for warehouse valuation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cadence",
            choices=["daily", "monthly"],
            help="Cadence label used for scheduled bucket deduplication.",
        )
        parser.add_argument(
            "--bucket-key",
            help="Explicit deduplication bucket key for externally scheduled runs.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow creating another scheduled snapshot in the same cadence bucket.",
        )

    def handle(self, *args, **options):
        cadence = options["cadence"]
        bucket_key = options["bucket_key"]
        force = options["force"]

        if cadence is None and bucket_key is None:
            raise CommandError("Provide --cadence or --bucket-key.")

        try:
            snapshot = inventory_snapshot_service.create_snapshot(
                trigger_source=InventorySnapshotTriggerSource.SCHEDULED,
                cadence=cadence,
                bucket_key=bucket_key,
                force=force,
            )
        except WarehouseGenericError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Created snapshot #{snapshot.id} with {snapshot.line_count} lines."
            )
        )
