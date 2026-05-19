#!/usr/bin/env python3
"""
Minimal Zebra barcode printer module.
Generates ZPL commands and sends them to a Zebra printer via TCP.
"""

import socket


def print_barcode(
    barcode: str,
    text: str = "",
    ip: str = "192.168.1.100",
    port: int = 9100,
    copies: int = 1,
    timeout: int = 5,
) -> None:
    """
    Print a barcode label on a Zebra printer.

    Args:
        barcode: The barcode data to encode (e.g., "123456789")
        text: Optional text to print above the barcode
        ip: Printer IP address
        port: Printer port (default 9100 for Zebra printers)
        copies: Number of copies to print
        timeout: Socket timeout in seconds

    Raises:
        ConnectionError: If unable to connect to printer
        TimeoutError: If connection times out
        ValueError: If barcode is empty
    """
    if not barcode:
        raise ValueError("Barcode cannot be empty")

    # Generate ZPL commands
    zpl = _generate_zpl(barcode, text)

    # Send to printer
    _send_to_printer(zpl, ip, port, copies, timeout)


def _generate_zpl(barcode: str, text: str = "") -> str:
    """
    Generate ZPL (Zebra Programming Language) commands for a barcode label.

    Args:
        barcode: Barcode data
        text: Optional text label

    Returns:
        ZPL command string
    """
    zpl_commands = [
        "^XA",  # Start label
        "^CI28",  # UTF-8 character encoding
        "^LL400^PW600",  # Label length 400, print width 600
        "^CF0,50",  # Default font, height 50
    ]

    # Add text if provided
    if text:
        zpl_commands.append(f"^FO50,50^FD{text}^FS")

    # Add barcode (Code-128)
    # ^BY: bar width, ratio, height
    # ^BC: Code-128 barcode
    zpl_commands.extend(
        [
            "^BY3,3,100",
            f"^FO50,150^BC^FD{barcode}^FS",
            "^XZ",  # End label
        ]
    )

    return "\n".join(zpl_commands)


def _send_to_printer(zpl: str, ip: str, port: int, copies: int, timeout: int) -> None:
    """
    Send ZPL commands to printer via TCP socket.

    Args:
        zpl: ZPL command string
        ip: Printer IP address
        port: Printer port
        copies: Number of copies to print
        timeout: Socket timeout in seconds

    Raises:
        ConnectionError: If unable to connect to printer
        TimeoutError: If connection times out
    """
    sock = None
    try:
        # Create socket and connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))

        # Send ZPL commands (UTF-8 encoded)
        zpl_bytes = zpl.encode("utf-8")
        for _ in range(copies):
            sock.sendall(zpl_bytes)

    except socket.timeout:
        raise TimeoutError(
            f"Connection to printer at {ip}:{port} timed out after {timeout}s"
        )
    except socket.error as e:
        raise ConnectionError(f"Failed to connect to printer at {ip}:{port}: {e}")
    finally:
        if sock:
            sock.close()


def main():
    """CLI interface for testing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Print barcode labels on Zebra printers"
    )
    parser.add_argument("barcode", help="Barcode data to print")
    parser.add_argument("-t", "--text", default="", help="Optional text label")
    parser.add_argument(
        "-i", "--ip", default="192.168.1.100", help="Printer IP address"
    )
    parser.add_argument("-p", "--port", type=int, default=9100, help="Printer port")
    parser.add_argument("-c", "--copies", type=int, default=1, help="Number of copies")
    parser.add_argument(
        "--timeout", type=int, default=5, help="Socket timeout in seconds"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print ZPL to stdout instead of sending to printer",
    )

    args = parser.parse_args()

    if args.dry_run:
        # Just print the ZPL for inspection
        zpl = _generate_zpl(args.barcode, args.text)
        print(zpl)
    else:
        try:
            print_barcode(
                barcode=args.barcode,
                text=args.text,
                ip=args.ip,
                port=args.port,
                copies=args.copies,
                timeout=args.timeout,
            )
            print(f"✓ Printed {args.copies} label(s) to {args.ip}:{args.port}")
        except (ConnectionError, TimeoutError, ValueError) as e:
            print(f"✗ Error: {e}")
            exit(1)
