from __future__ import annotations

from apps.warehouse.core.schemas.base import BaseSchema


class BarcodeSchema(BaseSchema):
    code: str
    barcode_type: str
    is_primary: bool
