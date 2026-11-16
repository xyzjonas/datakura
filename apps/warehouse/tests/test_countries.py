import pytest

from apps.warehouse.core.countries import COUNTRY_CODES, normalize_country_code


def test_all_iso_3166_alpha2_codes_are_known() -> None:
    assert len(COUNTRY_CODES) == 249
    assert {"CZ", "SK", "DE", "CN", "US", "XK"} & COUNTRY_CODES == {
        "CZ",
        "SK",
        "DE",
        "CN",
        "US",
    }


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("cz", "CZ"),
        (" de ", "DE"),
        ("CN", "CN"),
    ],
)
def test_normalize_country_code(value, expected) -> None:
    assert normalize_country_code(value) == expected


@pytest.mark.parametrize("value", ["XX", "CZE", "C", "1", "ZZ", "UK"])
def test_normalize_country_code_rejects_unknown(value) -> None:
    with pytest.raises(ValueError):
        normalize_country_code(value)
