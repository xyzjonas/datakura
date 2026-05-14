import pytest

from apps.warehouse.core.services.barcode_generator import (
    BarcodeGeneratorService,
    generate_barcode,
    _calculate_ean_check_digit,
    _generate_ean13,
    _generate_ean8,
    _generate_upc,
    _generate_serial,
    _generate_custom,
)
from apps.warehouse.models.barcode import BarcodeType


class TestCheckDigitCalculation:
    """Test EAN/UPC check digit calculation."""

    def test_calculate_ean_check_digit_valid(self):
        assert _calculate_ean_check_digit("012345678901") == "2"
        assert _calculate_ean_check_digit("400638133393") == "1"
        assert _calculate_ean_check_digit("978014300723") == "4"

    def test_calculate_ean_check_digit_all_zeros(self):
        assert _calculate_ean_check_digit("000000000000") == "0"

    def test_calculate_ean_check_digit_non_digit_raises(self):
        with pytest.raises(ValueError, match="must contain only digits"):
            _calculate_ean_check_digit("01234567890A")


class TestEAN13Generation:
    """Test EAN-13 barcode generation."""

    def test_generate_ean13_random(self):
        barcode = _generate_ean13()
        assert len(barcode) == 13
        assert barcode.isdigit()
        assert _calculate_ean_check_digit(barcode[:12]) == barcode[12]

    def test_generate_ean13_with_prefix(self):
        prefix = "012345678901"
        barcode = _generate_ean13(prefix=prefix)
        assert barcode == "0123456789012"
        assert len(barcode) == 13

    def test_generate_ean13_with_country_code(self):
        barcode = _generate_ean13(country_code="123")
        assert barcode.startswith("123")
        assert len(barcode) == 13
        assert barcode.isdigit()

    def test_generate_ean13_invalid_prefix_length(self):
        with pytest.raises(ValueError, match="must be exactly 12 digits"):
            _generate_ean13(prefix="123")

    def test_generate_ean13_invalid_prefix_non_digit(self):
        with pytest.raises(ValueError, match="must be exactly 12 digits"):
            _generate_ean13(prefix="01234567890A")

    def test_generate_ean13_invalid_country_code(self):
        with pytest.raises(ValueError, match="must be exactly 3 digits"):
            _generate_ean13(country_code="12")

    def test_generate_ean13_multiple_unique(self):
        barcodes = {_generate_ean13() for _ in range(100)}
        assert len(barcodes) > 95


class TestEAN8Generation:
    """Test EAN-8 barcode generation."""

    def test_generate_ean8_random(self):
        barcode = _generate_ean8()
        assert len(barcode) == 8
        assert barcode.isdigit()
        assert _calculate_ean_check_digit(barcode[:7]) == barcode[7]

    def test_generate_ean8_with_prefix(self):
        prefix = "0123456"
        barcode = _generate_ean8(prefix=prefix)
        assert barcode.startswith(prefix)
        assert len(barcode) == 8

    def test_generate_ean8_invalid_prefix_length(self):
        with pytest.raises(ValueError, match="must be exactly 7 digits"):
            _generate_ean8(prefix="123")

    def test_generate_ean8_invalid_prefix_non_digit(self):
        with pytest.raises(ValueError, match="must be exactly 7 digits"):
            _generate_ean8(prefix="012345A")

    def test_generate_ean8_multiple_unique(self):
        barcodes = {_generate_ean8() for _ in range(100)}
        assert len(barcodes) > 95


class TestUPCGeneration:
    """Test UPC-A barcode generation."""

    def test_generate_upc_random(self):
        barcode = _generate_upc()
        assert len(barcode) == 12
        assert barcode.isdigit()
        assert _calculate_ean_check_digit(barcode[:11]) == barcode[11]

    def test_generate_upc_with_prefix(self):
        prefix = "01234567890"
        barcode = _generate_upc(prefix=prefix)
        assert barcode.startswith(prefix)
        assert len(barcode) == 12

    def test_generate_upc_invalid_prefix_length(self):
        with pytest.raises(ValueError, match="must be exactly 11 digits"):
            _generate_upc(prefix="123")

    def test_generate_upc_invalid_prefix_non_digit(self):
        with pytest.raises(ValueError, match="must be exactly 11 digits"):
            _generate_upc(prefix="0123456789A")

    def test_generate_upc_multiple_unique(self):
        barcodes = {_generate_upc() for _ in range(100)}
        assert len(barcodes) > 95


class TestSerialGeneration:
    """Test serial number generation."""

    def test_generate_serial_default(self):
        serial = _generate_serial()
        assert len(serial) == 10
        assert serial.isdigit()

    def test_generate_serial_custom_length(self):
        serial = _generate_serial(length=20)
        assert len(serial) == 20
        assert serial.isdigit()

    def test_generate_serial_with_prefix(self):
        serial = _generate_serial(length=10, prefix="SN")
        assert serial.startswith("SN")
        assert len(serial) == 10
        assert serial[2:].isdigit()

    def test_generate_serial_alphanumeric(self):
        serial = _generate_serial(length=10, numeric_only=False)
        assert len(serial) == 10
        assert serial.isalnum()

    def test_generate_serial_alphanumeric_with_prefix(self):
        serial = _generate_serial(length=15, prefix="PROD", numeric_only=False)
        assert serial.startswith("PROD")
        assert len(serial) == 15
        assert serial.isalnum()

    def test_generate_serial_invalid_length(self):
        with pytest.raises(ValueError, match="must be positive"):
            _generate_serial(length=0)

        with pytest.raises(ValueError, match="must be positive"):
            _generate_serial(length=-1)

    def test_generate_serial_prefix_too_long(self):
        with pytest.raises(ValueError, match="must be less than total length"):
            _generate_serial(length=5, prefix="TOOLONG")

    def test_generate_serial_multiple_unique(self):
        serials = {_generate_serial() for _ in range(100)}
        assert len(serials) > 95


class TestCustomGeneration:
    """Test custom barcode generation."""

    def test_generate_custom_default(self):
        barcode = _generate_custom()
        assert len(barcode) == 12
        assert barcode.isalnum()

    def test_generate_custom_length(self):
        barcode = _generate_custom(length=20)
        assert len(barcode) == 20

    def test_generate_custom_with_prefix(self):
        barcode = _generate_custom(length=15, prefix="CUST")
        assert barcode.startswith("CUST")
        assert len(barcode) == 15

    def test_generate_custom_digits_only(self):
        barcode = _generate_custom(
            length=10, include_letters=False, include_digits=True
        )
        assert len(barcode) == 10
        assert barcode.isdigit()

    def test_generate_custom_letters_only(self):
        barcode = _generate_custom(
            length=10, include_letters=True, include_digits=False
        )
        assert len(barcode) == 10
        assert barcode.isalpha()
        assert barcode.isupper()

    def test_generate_custom_invalid_charset(self):
        with pytest.raises(ValueError, match="Must include at least letters or digits"):
            _generate_custom(include_letters=False, include_digits=False)

    def test_generate_custom_invalid_length(self):
        with pytest.raises(ValueError, match="must be positive"):
            _generate_custom(length=0)

    def test_generate_custom_prefix_too_long(self):
        with pytest.raises(ValueError, match="must be less than total length"):
            _generate_custom(length=5, prefix="TOOLONG")


class TestGenerateBarcodeFunction:
    """Test the main generate_barcode function with BarcodeType enum."""

    def test_generate_ean13(self):
        barcode = generate_barcode(BarcodeType.EAN13)
        assert len(barcode) == 13
        assert barcode.isdigit()

    def test_generate_ean13_with_string(self):
        barcode = generate_barcode("EAN13")
        assert len(barcode) == 13
        assert barcode.isdigit()

    def test_generate_ean13_with_kwargs(self):
        barcode = generate_barcode(BarcodeType.EAN13, country_code="999")
        assert barcode.startswith("999")

    def test_generate_ean8(self):
        barcode = generate_barcode(BarcodeType.EAN8)
        assert len(barcode) == 8
        assert barcode.isdigit()

    def test_generate_upc(self):
        barcode = generate_barcode(BarcodeType.UPC)
        assert len(barcode) == 12
        assert barcode.isdigit()

    def test_generate_serial(self):
        barcode = generate_barcode(BarcodeType.SERIAL, length=15, prefix="SER")
        assert barcode.startswith("SER")
        assert len(barcode) == 15

    def test_generate_custom(self):
        barcode = generate_barcode(
            BarcodeType.CUSTOM,
            length=10,
            include_letters=False,
            include_digits=True,
        )
        assert len(barcode) == 10
        assert barcode.isdigit()

    def test_generate_gs1_128_not_implemented(self):
        with pytest.raises(NotImplementedError, match="GS1-128"):
            generate_barcode(BarcodeType.GS1_128)

    def test_generate_sscc_not_implemented(self):
        with pytest.raises(NotImplementedError, match="SSCC"):
            generate_barcode(BarcodeType.SSCC)

    def test_generate_qr_not_implemented(self):
        with pytest.raises(NotImplementedError, match="QR code"):
            generate_barcode(BarcodeType.QR)


class TestBarcodeGeneratorService:
    """Test the BarcodeGeneratorService class."""

    def test_service_generate_ean13(self):
        barcode = BarcodeGeneratorService.generate(BarcodeType.EAN13)
        assert len(barcode) == 13
        assert barcode.isdigit()

    def test_service_generate_with_prefix(self):
        barcode = BarcodeGeneratorService.generate(
            BarcodeType.EAN13,
            prefix="012345678901",
        )
        assert barcode == "0123456789012"

    def test_service_generate_serial_with_kwargs(self):
        barcode = BarcodeGeneratorService.generate(
            BarcodeType.SERIAL,
            prefix="TEST",
            length=12,
            numeric_only=False,
        )
        assert barcode.startswith("TEST")
        assert len(barcode) == 12


class TestCheckDigitValidation:
    """Test check digit validation."""

    def test_validate_ean13_valid(self):
        assert BarcodeGeneratorService.validate_check_digit(
            "0123456789012", BarcodeType.EAN13
        )
        assert BarcodeGeneratorService.validate_check_digit(
            "4006381333931", BarcodeType.EAN13
        )

    def test_validate_ean13_invalid(self):
        assert not BarcodeGeneratorService.validate_check_digit(
            "0123456789013", BarcodeType.EAN13
        )

    def test_validate_ean13_wrong_length(self):
        assert not BarcodeGeneratorService.validate_check_digit(
            "012345678901", BarcodeType.EAN13
        )

    def test_validate_ean13_non_digit(self):
        assert not BarcodeGeneratorService.validate_check_digit(
            "012345678901A", BarcodeType.EAN13
        )

    def test_validate_ean8_valid(self):
        assert BarcodeGeneratorService.validate_check_digit(
            "01234565", BarcodeType.EAN8
        )

    def test_validate_ean8_invalid(self):
        assert not BarcodeGeneratorService.validate_check_digit(
            "01234566", BarcodeType.EAN8
        )

    def test_validate_upc_valid(self):
        assert BarcodeGeneratorService.validate_check_digit(
            "012345678905", BarcodeType.UPC
        )

    def test_validate_upc_invalid(self):
        assert not BarcodeGeneratorService.validate_check_digit(
            "012345678906", BarcodeType.UPC
        )

    def test_validate_unsupported_type(self):
        with pytest.raises(NotImplementedError):
            BarcodeGeneratorService.validate_check_digit("123456", BarcodeType.SERIAL)

    def test_validate_with_string_type(self):
        assert BarcodeGeneratorService.validate_check_digit("0123456789012", "EAN13")


class TestGeneratedBarcodesValidity:
    """Test that generated barcodes pass validation."""

    def test_generated_ean13_is_valid(self):
        for _ in range(10):
            barcode = generate_barcode(BarcodeType.EAN13)
            assert BarcodeGeneratorService.validate_check_digit(
                barcode, BarcodeType.EAN13
            )

    def test_generated_ean8_is_valid(self):
        for _ in range(10):
            barcode = generate_barcode(BarcodeType.EAN8)
            assert BarcodeGeneratorService.validate_check_digit(
                barcode, BarcodeType.EAN8
            )

    def test_generated_upc_is_valid(self):
        for _ in range(10):
            barcode = generate_barcode(BarcodeType.UPC)
            assert BarcodeGeneratorService.validate_check_digit(
                barcode, BarcodeType.UPC
            )
