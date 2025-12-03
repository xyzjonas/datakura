import pytest

from apps.warehouse.management.commands.import_products_csv import ProductRow


@pytest.mark.parametrize(
    "str_in, expected",
    [
        (
            "ISO_7380,_BN_6404:ISO 7380, BN 6404",
            {
                "ISO_7380": "",
                "_BN_6404": "ISO 7380",
                "BN 6404": "",
            },
        ),
        (
            "DIN:931;ISO:4014;ČSN :021101",
            {
                "DIN": "931",
                "ISO": "4014",
                "ČSN": "021101",
            },
        ),
        (
            "DIN:_931,_ISO:_4014,_ČSN:_021103.55:DIN: 931, ISO: 4014, ČSN: 021103.55",
            {"DIN": "931", "ISO": "4014", "ČSN": "021103.55"},
        ),
    ],
)
def test_validate_attributes(str_in, expected):
    assert ProductRow.parse_attrs(str_in) == expected
