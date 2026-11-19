from __future__ import annotations

from pydantic import Field

from ninja import Schema

from apps.warehouse.core.schemas.base import BaseResponse, BaseSchema
from apps.warehouse.models.settings import CodeSequence


class ExchangeRateSchema(Schema):
    """Base currency units per 1 unit of `currency`"""

    currency: str
    rate: float


class ExchangeRateUpdateSchema(Schema):
    currency: str
    rate: float = Field(gt=0, lt=1_000_000)


class GlobalSettingsSchema(BaseSchema):
    # 0 = no minimum
    minimum_item_value: float
    # 0 = no guard
    minimum_markup_percent: float
    code_sequence: CodeSequence
    # the currency the company does its taxes in
    base_currency: str
    # currencies that can be used at all (base one + the ones customers can be invoiced in)
    supported_currencies: list[str]
    # user defined rates to the base currency, one per supported non-base currency
    exchange_rates: list[ExchangeRateSchema]


class GlobalSettingsUpdateSchema(Schema):
    # every field is optional - None = keep the current value
    minimum_item_value: float | None = Field(default=None, ge=0)
    minimum_markup_percent: float | None = Field(default=None, ge=0, le=100000)
    code_sequence: CodeSequence | None = None  # None = keep current
    base_currency: str | None = None  # changing it drops the exchange rates
    # upserts the given rates (other ones are kept)
    exchange_rates: list[ExchangeRateUpdateSchema] | None = None


class GetGlobalSettingsResponse(BaseResponse):
    data: GlobalSettingsSchema
