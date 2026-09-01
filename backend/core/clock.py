"""
Wall-clock helper.

``Thread.date_created`` and ``Message.timestamp`` are epoch **milliseconds**,
because that is what the browser DTOs carry (a JS ``Date`` is constructed
straight from them). Everything that stamps one of those columns goes through
:func:`now_ms` so the unit is decided in exactly one place.
"""

from __future__ import annotations

from django.utils import timezone


def now_ms() -> int:
    """Current wall-clock time as epoch milliseconds."""
    return int(timezone.now().timestamp() * 1000)
