from django.core.management.base import BaseCommand

from apps.warehouse.core.services.data_import.progress import ImportProgress
from apps.warehouse.core.services.norm_backfill import norm_backfill_service


class Command(BaseCommand):
    help = "Fill product norms and customs nomenclature from the legacy product metas"

    def handle(self, *args, **options):
        def show(snapshot) -> None:
            self.stdout.write(
                f"\r{snapshot.percent:5.1f} % ({snapshot.stage_done}/"
                f"{snapshot.stage_total})",
                ending="",
            )

        result = norm_backfill_service.run(ImportProgress(show))
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {result.products_scanned} products, "
                f"{result.norms_linked} norms linked ({result.norms_created} norms "
                f"created, {result.aliases_linked} aliases), "
                f"{result.customs_filled} customs groups filled"
            )
        )
        self.stdout.write(
            f"Still without norm: {result.without_norm}, "
            f"without customs group: {result.without_customs}"
        )
        if result.invalid_count:
            self.stdout.write(
                self.style.WARNING(f"{result.invalid_count} invalid values:")
            )
            for issue in result.invalid:
                self.stdout.write(
                    f"  {issue.product_code}: {issue.key}={issue.value!r} "
                    f"({issue.reason})"
                )
