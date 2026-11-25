import base64

import pytest

from apps.warehouse.core.services import barcode_svg


def test_every_symbol_pattern_is_11_modules_wide_stop_is_13() -> None:
    widths = [sum(int(w) for w in p) for p in barcode_svg._PATTERNS]

    assert len(widths) == 107
    assert set(widths[:106]) == {11}
    assert widths[106] == 13


@pytest.mark.parametrize(
    "text, expected",
    [
        ("A", [104, 33, 34, 106]),  # (104 + 33 * 1) % 103 == 34
        ("PJJ123C", [104, 48, 42, 42, 17, 18, 19, 35, 55, 106]),
        (" ", [104, 0, 1, 106]),
    ],
)
def test_encode_symbols_and_checksum(text, expected) -> None:
    assert barcode_svg.encode(text) == expected


@pytest.mark.parametrize("text", ["", "ž", "a\tb", "\n"])
def test_not_encodable_texts(text) -> None:
    assert not barcode_svg.is_encodable(text)
    assert barcode_svg.to_data_uri(text) is None
    with pytest.raises(ValueError):
        barcode_svg.encode(text)


def test_data_uri_is_an_svg_with_bars() -> None:
    uri = barcode_svg.to_data_uri("OBJ-0001")

    assert uri is not None and uri.startswith("data:image/svg+xml;base64,")
    svg = base64.b64decode(uri.split(",", 1)[1]).decode()
    assert svg.startswith("<svg") and svg.count("<rect") > 10
