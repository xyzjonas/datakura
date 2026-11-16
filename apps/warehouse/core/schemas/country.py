from typing import Annotated

from ninja import Schema
from pydantic import AfterValidator

from apps.warehouse.core.countries import normalize_country_code

# ISO 3166-1 alpha-2 code, upper-cased; blank is treated as "not set"
CountryCode = Annotated[str, AfterValidator(lambda v: normalize_country_code(v))]


class OriginCountryBulkSchema(Schema):
    """Set (or, with null, clear) the country on every item of an order."""

    country: CountryCode | None = None
