"""Helpers shared by the JSON data importers"""

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from loguru import logger

from apps.warehouse.core.services.data_import.errors import DataImportError

ModelT = TypeVar("ModelT", bound=BaseModel)


def read_text(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise DataImportError(f"Cannot read '{path}': {exc}") from exc


def decode_bytes(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DataImportError(f"Input is not valid UTF-8: {exc}") from exc


def parse_rows(raw: str) -> list[Any]:
    """JSON document holding either a list of records or a single record"""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DataImportError(f"Invalid JSON: {exc}") from exc
    return payload if isinstance(payload, list) else [payload]


def validate_rows(model: type[ModelT], rows: list[Any]) -> list[tuple[int, ModelT]]:
    """Validate every row, report all the failures at once"""
    valid: list[tuple[int, ModelT]] = []
    errors: list[str] = []
    logger.debug("Validating {} {} records", len(rows), model.__name__)
    for index, row in enumerate(rows):
        try:
            valid.append((index, model.model_validate(row)))
        except ValidationError as exc:
            errors.append(f"Record #{index}: {exc}")
    if errors:
        logger.error(
            "{}: {} of {} records are invalid", model.__name__, len(errors), len(rows)
        )
        raise DataImportError("\n".join(errors))
    return valid
