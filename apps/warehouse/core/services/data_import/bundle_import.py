"""Orchestrates the whole legacy data import - products, customers, warehouse stock"""

from dataclasses import dataclass
from typing import Callable, TypeVar

from django.db import transaction
from loguru import logger

from apps.warehouse.core.exceptions import DataImportFailedError
from apps.warehouse.core.schemas.data_import import (
    CustomerImportResultSchema,
    DataImportResultSchema,
    ProductImportResultSchema,
    WarehouseImportResultSchema,
)
from apps.warehouse.core.services.data_import.common import decode_bytes
from apps.warehouse.core.services.data_import.customer_import import (
    CustomerImportService,
)
from apps.warehouse.core.services.data_import.errors import DataImportError
from apps.warehouse.core.services.data_import.product_import import (
    ProductImportService,
)
from apps.warehouse.core.services.data_import.progress import ImportProgress
from apps.warehouse.core.services.data_import.stock_import import StockImportService

T = TypeVar("T")


@dataclass
class WarehouseFile:
    warehouse: str
    content: bytes

    @classmethod
    def pair(cls, warehouses: list[str], contents: list[bytes]) -> list[WarehouseFile]:
        if len(warehouses) != len(contents):
            raise DataImportFailedError(
                f"Got {len(warehouses)} warehouse ids but {len(contents)} files"
            )
        return [cls(w, c) for w, c in zip(warehouses, contents)]


class DataImportBundleService:
    """
    Runs the importers in dependency order (products -> customers -> stock) in a
    single transaction: any failure leaves the database untouched.
    """

    @transaction.atomic
    def run(
        self,
        products: bytes | None = None,
        customers: bytes | None = None,
        warehouses: list[WarehouseFile] | None = None,
        progress: ImportProgress | None = None,
    ) -> DataImportResultSchema:
        logger.info(
            "Data import started: products={}, customers={}, warehouses={}",
            products is not None,
            customers is not None,
            [w.warehouse for w in warehouses or []],
        )
        result = DataImportResultSchema(warehouses=[])
        progress = progress or ImportProgress()

        if products is not None:
            logger.info("Data import: products ({} bytes)", len(products))
            summary = self._step("products", products, ProductImportService(), progress)
            result.products = ProductImportResultSchema(
                created=summary.created_count,
                updated=summary.updated_count,
                skipped=summary.skipped_count,
                barcodes_attached=summary.barcodes_attached,
                warnings=summary.warnings,
            )

        if customers is not None:
            logger.info("Data import: customers ({} bytes)", len(customers))
            summary = self._step(
                "customers", customers, CustomerImportService(), progress
            )
            result.customers = CustomerImportResultSchema(
                created=summary.created_count,
                updated=summary.updated_count,
                contacts=summary.contacts_count,
                groups_created=summary.groups_created,
                warnings=summary.warnings,
            )

        for file in warehouses or []:
            logger.info(
                "Data import: warehouse '{}' ({} bytes)",
                file.warehouse,
                len(file.content),
            )
            label = f"warehouse '{file.warehouse}'"
            service = self._guard(label, lambda: StockImportService(file.warehouse))
            summary = self._step(label, file.content, service, progress)
            result.warehouses.append(
                WarehouseImportResultSchema(
                    warehouse=service.warehouse_name,
                    warehouse_created=summary.warehouse_created,
                    locations_created=summary.locations_created,
                    locations_existing=summary.locations_existing,
                    items_created=summary.items_created,
                )
            )

        progress.finish()
        logger.info("Data import finished successfully")
        return result

    def _step(self, label: str, content: bytes, service, progress: ImportProgress):
        progress.begin_stage(label, weight=len(content))
        result = self._guard(
            label, lambda: service.import_from_json(decode_bytes(content), progress)
        )
        progress.end_stage()
        return result

    @staticmethod
    def total_weight(
        products: bytes | None,
        customers: bytes | None,
        warehouses: list[WarehouseFile] | None,
    ) -> int:
        """Size of all the inputs - the unit the overall percentage is based on"""
        return sum(len(c) for c in (products, customers) if c is not None) + sum(
            len(w.content) for w in warehouses or []
        )

    @staticmethod
    def _guard(label: str, action: Callable[[], T]) -> T:
        try:
            return action()
        except DataImportError as exc:
            logger.error("Data import step '{}' failed, rolling back all", label)
            raise DataImportFailedError(f"{label}: {exc}") from exc
