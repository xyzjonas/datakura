import pytest

from apps.warehouse.core.services.norms import ParsedNorm, parse_norms, pick_primary
from apps.warehouse.models.product import NormType

DIN, CSN, ISO = NormType.DIN, NormType.CSN, NormType.ISO


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("DIN 84", [(DIN, "84")]),
        ("DIN_84", [(DIN, "84")]),
        ("DIN84", [(DIN, "84")]),
        ("din 84", [(DIN, "84")]),
        ("  DIN   84  ", [(DIN, "84")]),
        ("CSN_021131", [(CSN, "021131")]),
        ("ČSN 021131", [(CSN, "021131")]),
        ("ISO 1234", [(ISO, "1234")]),
        ("ISO 4017-A", [(ISO, "4017-A")]),
        ("DIN 7991.", [(DIN, "7991")]),
        ("DIN-933", [(DIN, "933")]),
        # alias in a single value
        ("DIN 84, ISO 1207", [(DIN, "84"), (ISO, "1207")]),
        ("DIN 84 / DIN 84", [(DIN, "84")]),
        # harmonised norms: "EN" is no code, "ISO" is a second namespace
        ("DIN EN ISO 4017", [(DIN, "4017"), (ISO, "4017")]),
        ("DIN EN 4017", [(DIN, "4017")]),
    ],
)
def test_parse_norms(value, expected):
    assert parse_norms(value) == [ParsedNorm(t, c) for t, c in expected]


@pytest.mark.parametrize(
    "value",
    [None, "", "   ", "84", "DIN", "DIN ABC", "GOST 123", "EN 1234", "NF E 25-100"],
)
def test_parse_norms_unrecognised(value):
    assert parse_norms(value) == []


@pytest.mark.parametrize(
    ("norms", "expected"),
    [
        ([(ISO, "1"), (DIN, "2")], (DIN, "2")),
        ([(ISO, "1"), (CSN, "2")], (CSN, "2")),
        ([(CSN, "2"), (DIN, "3"), (DIN, "4")], (DIN, "3")),
        ([(ISO, "1")], (ISO, "1")),
    ],
)
def test_pick_primary_prefers_din(norms, expected):
    parsed = [ParsedNorm(t, c) for t, c in norms]
    assert pick_primary(parsed) == ParsedNorm(*expected)
