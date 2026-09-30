"""Worker side of the import: runs the bundle on staged files, reports progress"""

from typing import Any, TypedDict

from loguru import logger

from apps.warehouse.core.exceptions import DataImportFailedError
from apps.warehouse.core.services.data_import.bundle_import import (
    DataImportBundleService,
    WarehouseFile,
)
from apps.warehouse.core.services.data_import.progress import (
    ImportProgress,
    ProgressSink,
)
from apps.warehouse.core.services.data_import.staging import (
    discard_staged,
    read_staged,
)

STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"


class StagedWarehouse(TypedDict):
    warehouse: str
    path: str


def run_staged_import(
    products: str | None,
    customers: str | None,
    warehouses: list[StagedWarehouse],
    sink: ProgressSink | None = None,
) -> dict[str, Any]:
    """
    Always returns an envelope - `{"status", "result" | "error"}` - because expected
    import failures are a regular outcome, not a crashed task.
    """
    staged = [p for p in (products, customers) if p] + [w["path"] for w in warehouses]
    try:
        product_bytes = read_staged(products) if products else None
        customer_bytes = read_staged(customers) if customers else None
        warehouse_files = [
            WarehouseFile(w["warehouse"], read_staged(w["path"])) for w in warehouses
        ]

        service = DataImportBundleService()
        progress = ImportProgress(
            sink,
            total_weight=service.total_weight(
                product_bytes, customer_bytes, warehouse_files
            ),
        )
        result = service.run(
            products=product_bytes,
            customers=customer_bytes,
            warehouses=warehouse_files,
            progress=progress,
        )
        return {"status": STATUS_SUCCEEDED, "result": result.model_dump()}
    except DataImportFailedError as exc:
        logger.error("Data import failed: {}", exc)
        return {"status": STATUS_FAILED, "error": str(exc)}
    finally:
        discard_staged(staged)
