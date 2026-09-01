"""
Wall-clock helper.

``threads.date_created`` and ``messages.timestamp`` are epoch **milliseconds**,
because that is what the browser DTOs carry (a JS ``Date`` is constructed
straight from them). Everything that stamps one of those columns goes through
:func:`now_ms` so the unit is decided in exactly one place.
"""

from __future__ import annotations

from datetime import UTC, datetime


def now_ms() -> int:
    """Current wall-clock time as epoch milliseconds."""
    return int(datetime.now(UTC).timestamp() * 1000)
