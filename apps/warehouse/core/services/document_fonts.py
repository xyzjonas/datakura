"""Fonts selectable for the printed documents.

Everything is bundled in `apps/warehouse/fonts` (SIL OFL, Latin + Latin Extended merged
into one WOFF2 per weight) and inlined into the document as a data URI - nothing is ever
downloaded, so the documents look the same in an air-gapped environment.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from functools import cache
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parents[2] / "fonts"
WEIGHTS = (400, 700)
DEFAULT_FONT = "system"


@dataclass(frozen=True)
class DocumentFont:
    key: str
    label: str
    stack: str  # CSS font-family value (with fallbacks)
    bundled: bool = True


FONTS: dict[str, DocumentFont] = {
    f.key: f
    for f in (
        # not bundled: whatever the machine has (DejaVu is a WeasyPrint dependency)
        DocumentFont(
            DEFAULT_FONT, "Systémové (DejaVu Sans)", '"DejaVu Sans", sans-serif', False
        ),
        DocumentFont("open-sans", "Open Sans", '"Open Sans", sans-serif'),
        DocumentFont("roboto", "Roboto", '"Roboto", sans-serif'),
        DocumentFont("inter", "Inter", '"Inter", sans-serif'),
        DocumentFont("lato", "Lato", '"Lato", sans-serif'),
        DocumentFont("source-sans-3", "Source Sans 3", '"Source Sans 3", sans-serif'),
        DocumentFont("noto-serif", "Noto Serif", '"Noto Serif", serif'),
    )
}


def resolve(key: str) -> DocumentFont:
    return FONTS.get(key) or FONTS[DEFAULT_FONT]


@cache
def _data_uri(key: str, weight: int) -> str:
    raw = (FONTS_DIR / key / f"{key}-{weight}.woff2").read_bytes()
    return f"data:font/woff2;base64,{base64.b64encode(raw).decode()}"


def font_face_css(key: str) -> str:
    """`@font-face` rules of a bundled font, empty for the system font."""
    font = resolve(key)
    if not font.bundled:
        return ""
    family = font.stack.split(",")[0]
    return "\n".join(
        f"@font-face {{ font-family: {family}; font-weight: {w}; font-style: normal; "
        f'src: url("{_data_uri(font.key, w)}") format("woff2"); }}'
        for w in WEIGHTS
    )
