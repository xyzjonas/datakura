from decimal import Decimal

from pydantic import BaseModel

from apps.warehouse.core.schemas.base import BaseResponse


class TotalInventoryValue(BaseModel):
    value: Decimal


class TotalInventoryValueResponse(BaseResponse):
    data: TotalInventoryValue
