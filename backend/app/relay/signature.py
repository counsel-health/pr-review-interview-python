"""
HMAC-SHA256 signing and verification for Relay webhooks.

Relay is the upstream messaging provider. Both directions of the integration
share one secret (``RELAY_WEBHOOK_SECRET``): outbound payloads are signed with
:func:`sign_relay_payload`, inbound ones are checked with
:func:`verify_relay_signature`.

Verification uses a constant-time compare so an attacker can't recover the
expected digest byte-by-byte from response timing.
"""

from __future__ import annotations

import hmac
from hashlib import sha256

from app.config import relay_webhook_secret


def _resolve_secret(secret: str | None) -> str | None:
    if secret is not None:
        return secret
    return relay_webhook_secret()


def sign_relay_payload(raw_body: bytes | str, secret: str | None = None) -> str:
    """Hex-encoded HMAC-SHA256 of ``raw_body``."""
    resolved = _resolve_secret(secret)
    if not resolved:
        raise ValueError("RELAY_WEBHOOK_SECRET is not set")
    return _digest(raw_body, resolved)


def verify_relay_signature(
    raw_body: bytes | str,
    signature_header: str | None,
    secret: str | None = None,
) -> bool:
    """
    Check a webhook's signature header against the shared secret.

    Returns False — never raises — when the secret is unconfigured or the
    header is absent, so an unsigned request is rejected rather than crashing
    the handler.
    """
    resolved = _resolve_secret(secret)
    if not resolved:
        return False
    if not signature_header:
        return False
    return hmac.compare_digest(_digest(raw_body, resolved), signature_header)


def _digest(raw_body: bytes | str, secret: str) -> str:
    body = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
    return hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()
