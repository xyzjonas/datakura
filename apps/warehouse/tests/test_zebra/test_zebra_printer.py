from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.warehouse.core import zebra_printer


EXAMPLE_LABEL = Path(__file__).parent / "example_label.zpl"


def test_generate_zpl_matches_example_label():
    expected = EXAMPLE_LABEL.read_text().strip()
    actual = zebra_printer._generate_zpl("WMS-WIDGET-001", "Premium Widget v2.0")
    assert actual.strip() == expected


def test_generate_zpl_without_text_omits_text_field():
    zpl = zebra_printer._generate_zpl("ABC-123")
    assert "^FD" in zpl
    assert (
        "^BCABC-123" not in zpl
    )  # text-only ^FD should not appear at the text position
    assert "^FO50,150^BC^FDABC-123^FS" in zpl


def test_print_barcode_empty_raises():
    with pytest.raises(ValueError, match="cannot be empty"):
        zebra_printer.print_barcode("")


def test_print_barcode_sends_zpl_per_copy():
    fake_sock = MagicMock()
    with patch("socket.socket", return_value=fake_sock):
        zebra_printer.print_barcode(
            "ABC-123", text="Hello", ip="10.0.0.1", port=9100, copies=3
        )

    fake_sock.connect.assert_called_once_with(("10.0.0.1", 9100))
    assert fake_sock.sendall.call_count == 3
    fake_sock.close.assert_called_once()
