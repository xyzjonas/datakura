"""
Sequential document codes (orders, calculations, ...).

Layout depends on the global `code_sequence` setting:

- monthly: ``{prefix}{YYYY}{MM}{NNNN}``  e.g. ``OP2026110003``
- yearly:  ``{prefix}{YYYY}{NNNNN}``     e.g. ``OP202600003``

The sequence number is inferred from the highest existing code of the current
period (not COUNT) so deleting a document never causes a collision. Codes in a
different layout (e.g. created before the setting was changed) are ignored.
"""

import re
from datetime import datetime

from django.db.models import QuerySet
from django.utils import timezone

from apps.warehouse.models.settings import CodeSequence, GlobalSettings

_SEQUENCE_WIDTH = {CodeSequence.MONTHLY: 4, CodeSequence.YEARLY: 5}


def period_prefix(prefix: str, sequence: CodeSequence, now: datetime) -> str:
    if sequence == CodeSequence.MONTHLY:
        return f"{prefix}{now.year}{now.month:02d}"
    return f"{prefix}{now.year}"


def generate_next_sequential_code(
    *,
    queryset: QuerySet,
    prefix: str,
    field_name: str = "code",
    sequence: CodeSequence | None = None,
) -> str:
    """Next free code for *prefix* in the period given by the global setting."""
    sequence = CodeSequence(sequence or GlobalSettings.load().code_sequence)
    now = timezone.now()
    base = period_prefix(prefix, sequence, now)
    width = _SEQUENCE_WIDTH[sequence]
    pattern = re.compile(rf"^{re.escape(base)}(\d{{{width}}})$")

    codes = (
        queryset.filter(**{f"{field_name}__startswith": base})
        .order_by(f"-{field_name}")
        .values_list(field_name, flat=True)
    )
    last = 0
    for code in codes.iterator():
        if match := pattern.match(str(code)):
            last = int(match.group(1))
            break  # fixed width + descending order: first match is the highest
    return f"{base}{last + 1:0{width}d}"
