"""
Outbound Relay client — an in-process stub for Relay's SMS/push API.

In production this would POST to Relay to deliver an SMS or push to a member of
a patient's care team. Locally it just logs the "send", so the app runs offline
with no network, API key, or cost — the same offline-stub principle as
``app/ai/summarize.py``.

Relay, like most messaging providers, dedupes by idempotency key: sending the
same key twice delivers once.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

#: Idempotency keys Relay has already accepted, standing in for the provider's
#: server-side dedupe table.
_delivered_keys: set[str] = set()


async def send_care_team_notification(
    thread_id: str,
    physician_id: str,
    body: str,
    idempotency_key: str | None = None,
) -> None:
    """
    Deliver a care-team notification through Relay.

    When ``idempotency_key`` is given, repeat sends carrying the same key are
    delivered once. Callers on a retryable path — an at-least-once queue
    handler, say — should always pass one.
    """
    if idempotency_key and idempotency_key in _delivered_keys:
        logger.info(
            "[relay] notification already sent (idempotency hit) "
            "physician=%s thread=%s",
            physician_id,
            thread_id,
        )
        return
    if idempotency_key:
        _delivered_keys.add(idempotency_key)

    logger.info(
        "[relay] sent SMS physician=%s thread=%s: %s", physician_id, thread_id, body
    )
