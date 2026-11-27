"""Code 128 (subset B) barcode as an SVG data URI - printed on the documents."""

from __future__ import annotations

import base64

# bar/space widths of the symbols 0..106 (106 = stop, 13 modules, the others 11)
_PATTERNS = (
    "212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 "
    "221312 231212 112232 122132 122231 113222 123122 123221 223211 221132 "
    "221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 "
    "212123 212321 232121 111323 131123 131321 112313 132113 132311 211313 "
    "231113 231311 112133 112331 132131 113123 113321 133121 313121 211331 "
    "231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 "
    "314111 221411 431111 111224 111422 121124 121421 141122 141221 112214 "
    "112412 122114 122411 142112 142211 241211 221114 413111 241112 134111 "
    "111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 "
    "214121 412121 111143 111341 131141 114113 114311 411113 411311 113141 "
    "114131 311141 411131 211412 211214 211232 2331112"
).split()
_START_B = 104
_STOP = 106
_QUIET_ZONE = 10  # modules


def is_encodable(text: str) -> bool:
    return bool(text) and all(32 <= ord(c) <= 126 for c in text)


def encode(text: str) -> list[int]:
    """Symbol values of the text incl. start, checksum and stop."""
    if not is_encodable(text):
        raise ValueError("Code 128B encodes printable ASCII only")
    values = [ord(c) - 32 for c in text]
    checksum = (
        _START_B + sum(value * position for position, value in enumerate(values, 1))
    ) % 103
    return [_START_B, *values, checksum, _STOP]


def to_svg(text: str, module_width: int = 2, height: int = 40) -> str:
    """SVG of the barcode, `module_width` px per narrowest bar."""
    x = _QUIET_ZONE
    bars: list[str] = []
    for symbol in encode(text):
        for index, width in enumerate(_PATTERNS[symbol]):
            if index % 2 == 0:  # even positions are the bars
                bars.append(
                    f'<rect x="{x * module_width}" width="{int(width) * module_width}" height="{height}"/>'
                )
            x += int(width)
    total = (x + _QUIET_ZONE) * module_width
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{height}" '
        f'viewBox="0 0 {total} {height}" shape-rendering="crispEdges">'
        f'<rect width="{total}" height="{height}" fill="#fff"/>'
        f'<g fill="#000">{"".join(bars)}</g></svg>'
    )


def to_data_uri(text: str) -> str | None:
    """`None` when the text cannot be encoded."""
    if not is_encodable(text):
        return None
    svg = to_svg(text).encode()
    return f"data:image/svg+xml;base64,{base64.b64encode(svg).decode()}"
