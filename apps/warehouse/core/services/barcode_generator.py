from __future__ import annotations

import random
import string
from typing import Any

from apps.warehouse.models.barcode import BarcodeType


def _calculate_ean_check_digit(code: str) -> str:
    """Calculate EAN/UPC check digit using modulo 10 algorithm."""
    if not code.isdigit():
        raise ValueError("Code must contain only digits")

    total = 0
    for i, digit in enumerate(reversed(code)):
        multiplier = 3 if i % 2 == 0 else 1
        total += int(digit) * multiplier

    check_digit = (10 - (total % 10)) % 10
    return str(check_digit)


def _generate_ean13(
    prefix: str | None = None,
    country_code: str = "000",
) -> str:
    """
    Generate EAN-13 barcode.

    Args:
        prefix: Optional 12-digit prefix (check digit will be calculated)
        country_code: 3-digit country code (default: 000 for internal use)

    Returns:
        13-digit EAN-13 barcode with check digit
    """
    if prefix:
        if len(prefix) != 12 or not prefix.isdigit():
            raise ValueError("Prefix must be exactly 12 digits")
        base_code = prefix
    else:
        if len(country_code) != 3 or not country_code.isdigit():
            raise ValueError("Country code must be exactly 3 digits")
        manufacturer_code = "".join(random.choices(string.digits, k=4))
        product_code = "".join(random.choices(string.digits, k=5))
        base_code = country_code + manufacturer_code + product_code

    check_digit = _calculate_ean_check_digit(base_code)
    return base_code + check_digit


def _generate_ean8(prefix: str | None = None) -> str:
    """
    Generate EAN-8 barcode.

    Args:
        prefix: Optional 7-digit prefix (check digit will be calculated)

    Returns:
        8-digit EAN-8 barcode with check digit
    """
    if prefix:
        if len(prefix) != 7 or not prefix.isdigit():
            raise ValueError("Prefix must be exactly 7 digits")
        base_code = prefix
    else:
        base_code = "".join(random.choices(string.digits, k=7))

    check_digit = _calculate_ean_check_digit(base_code)
    return base_code + check_digit


def _generate_upc(prefix: str | None = None) -> str:
    """
    Generate UPC-A barcode.

    Args:
        prefix: Optional 11-digit prefix (check digit will be calculated)

    Returns:
        12-digit UPC-A barcode with check digit
    """
    if prefix:
        if len(prefix) != 11 or not prefix.isdigit():
            raise ValueError("Prefix must be exactly 11 digits")
        base_code = prefix
    else:
        base_code = "".join(random.choices(string.digits, k=11))

    check_digit = _calculate_ean_check_digit(base_code)
    return base_code + check_digit


def _generate_serial(
    length: int = 10,
    prefix: str = "",
    numeric_only: bool = True,
) -> str:
    """
    Generate a serial number.

    Args:
        length: Total length of serial number (including prefix)
        prefix: Optional prefix for the serial number
        numeric_only: If True, generate numeric only; if False, alphanumeric

    Returns:
        Serial number string
    """
    if length <= 0:
        raise ValueError("Length must be positive")

    if len(prefix) >= length:
        raise ValueError("Prefix length must be less than total length")

    remaining_length = length - len(prefix)

    if numeric_only:
        random_part = "".join(random.choices(string.digits, k=remaining_length))
    else:
        random_part = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=remaining_length)
        )

    return prefix + random_part


def _generate_custom(
    length: int = 12,
    prefix: str = "",
    include_letters: bool = True,
    include_digits: bool = True,
) -> str:
    """
    Generate a custom barcode.

    Args:
        length: Total length of the barcode (including prefix)
        prefix: Optional prefix for the barcode
        include_letters: Include uppercase letters in generation
        include_digits: Include digits in generation

    Returns:
        Custom barcode string
    """
    if length <= 0:
        raise ValueError("Length must be positive")

    if len(prefix) >= length:
        raise ValueError("Prefix length must be less than total length")

    if not include_letters and not include_digits:
        raise ValueError("Must include at least letters or digits")

    charset = ""
    if include_letters:
        charset += string.ascii_uppercase
    if include_digits:
        charset += string.digits

    remaining_length = length - len(prefix)
    random_part = "".join(random.choices(charset, k=remaining_length))

    return prefix + random_part


def generate_barcode(
    barcode_type: BarcodeType | str,
    prefix: str | None = None,
    **kwargs,
) -> str:
    """
    Generate a barcode of the specified type.

    Args:
        barcode_type: Type of barcode to generate
        prefix: Optional prefix for the barcode (meaning varies by type)
        **kwargs: Additional type-specific parameters

    Returns:
        Generated barcode string

    Raises:
        NotImplementedError: For barcode types that are not yet implemented
        ValueError: For invalid parameters

    Examples:
        >>> generate_barcode(BarcodeType.EAN13)
        '0001234567890'

        >>> generate_barcode(BarcodeType.EAN13, prefix="012345678901")
        '0123456789012'

        >>> generate_barcode(BarcodeType.SERIAL, length=8, prefix="SN")
        'SN123456'

        >>> generate_barcode(BarcodeType.CUSTOM, length=10, include_letters=False)
        '1234567890'
    """
    if isinstance(barcode_type, str):
        barcode_type = BarcodeType(barcode_type)

    match barcode_type:
        case BarcodeType.EAN13:
            country_code = kwargs.get("country_code", "000")
            return _generate_ean13(prefix=prefix, country_code=country_code)

        case BarcodeType.EAN8:
            return _generate_ean8(prefix=prefix)

        case BarcodeType.UPC:
            return _generate_upc(prefix=prefix)

        case BarcodeType.SERIAL:
            length = kwargs.get("length", 10)
            numeric_only = kwargs.get("numeric_only", True)
            return _generate_serial(
                length=length,
                prefix=prefix or "",
                numeric_only=numeric_only,
            )

        case BarcodeType.CUSTOM:
            length = kwargs.get("length", 12)
            include_letters = kwargs.get("include_letters", True)
            include_digits = kwargs.get("include_digits", True)
            return _generate_custom(
                length=length,
                prefix=prefix or "",
                include_letters=include_letters,
                include_digits=include_digits,
            )

        case BarcodeType.GS1_128:
            raise NotImplementedError(
                "GS1-128 barcode generation is not yet implemented. "
                "This format requires complex application identifier handling."
            )

        case BarcodeType.SSCC:
            raise NotImplementedError(
                "SSCC barcode generation is not yet implemented. "
                "This format requires GS1 company prefix and extension digit handling."
            )

        case BarcodeType.QR:
            raise NotImplementedError(
                "QR code generation is not yet implemented. "
                "Consider using a dedicated QR code library for this format."
            )

        case _:
            raise ValueError(f"Unknown barcode type: {barcode_type}")


class BarcodeGeneratorService:
    """Service for generating barcodes of various types."""

    @staticmethod
    def generate(
        barcode_type: BarcodeType | str,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate a barcode of the specified type.

        See generate_barcode() for full documentation.
        """
        return generate_barcode(barcode_type, prefix=prefix, **kwargs)

    @staticmethod
    def validate_check_digit(code: str, barcode_type: BarcodeType | str) -> bool:
        """
        Validate the check digit of a barcode.

        Args:
            code: The barcode to validate
            barcode_type: Type of barcode

        Returns:
            True if check digit is valid, False otherwise

        Raises:
            NotImplementedError: For barcode types without check digit validation
        """
        if isinstance(barcode_type, str):
            barcode_type = BarcodeType(barcode_type)

        match barcode_type:
            case BarcodeType.EAN13:
                if len(code) != 13 or not code.isdigit():
                    return False
                expected_check = _calculate_ean_check_digit(code[:12])
                return code[12] == expected_check

            case BarcodeType.EAN8:
                if len(code) != 8 or not code.isdigit():
                    return False
                expected_check = _calculate_ean_check_digit(code[:7])
                return code[7] == expected_check

            case BarcodeType.UPC:
                if len(code) != 12 or not code.isdigit():
                    return False
                expected_check = _calculate_ean_check_digit(code[:11])
                return code[11] == expected_check

            case _:
                raise NotImplementedError(
                    f"Check digit validation not implemented for {barcode_type}"
                )


barcode_generator_service = BarcodeGeneratorService()
