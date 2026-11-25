"""
Simulate an inbound Relay webhook against the locally-running app.

NOTE: This file is dev tooling for the interview exercise; it does not need to be
reviewed.

Signs a sample payload with ``RELAY_WEBHOOK_SECRET`` and POSTs it to
``/api/webhooks/relay``, so the whole inbound flow can be exercised offline::

    uv run relay-send                        # one inbound to the newest thread
    uv run relay-send --thread <id>          # target a specific thread
    uv run relay-send --from +15550000004    # spoof a different patient's number
    uv run relay-send --text "hello"         # custom body
    uv run relay-send --delivery-id dlv_1    # fixed delivery id (re-send)
    uv run relay-send --concurrent           # fire two deliveries at once
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import urllib.error
import urllib.request

from sqlalchemy import select

from app.db import dispose_engine, one
from app.relay.signature import sign_relay_payload
from app.schema import threads

DEFAULT_APP_URL = "http://localhost:8000"
DEFAULT_SECRET = "dev-secret"
DEFAULT_FROM = "+15550000001"
DEFAULT_TEXT = "Hi, this is an inbound message via Relay."


def send_one(
    app_url: str,
    secret: str,
    thread_id: str,
    delivery_id: str,
    sender: str,
    text: str,
) -> str:
    body = {
        "type": "msg",
        "delivery_id": delivery_id,
        "threadId": thread_id,
        "from": sender,
        "message": {"text": text},
        "isUrgent": "false",
    }
    raw = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(
        f"{app_url}/api/webhooks/relay",
        data=raw,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-relay-signature": sign_relay_payload(raw, secret),
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            return f"{response.status} {response.read().decode('utf-8')}"
    except urllib.error.HTTPError as exc:
        return f"{exc.code} {exc.read().decode('utf-8')}"
    except urllib.error.URLError as exc:
        return f"connection failed ({exc.reason}); is the API server running?"


async def newest_thread_id() -> str:
    row = await one(select(threads.c.id).order_by(threads.c.date_created.desc()))
    if row is None:
        raise SystemExit("no threads in the database; run `uv run migrate` to seed")
    return str(row["id"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="POST a signed sample Relay webhook at the local app."
    )
    parser.add_argument("--thread", default="", help="thread id to deliver to")
    parser.add_argument("--from", dest="sender", default=DEFAULT_FROM)
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--delivery-id", dest="delivery_id", default="")
    parser.add_argument("--concurrent", action="store_true")
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    app_url = os.environ.get("APP_URL", DEFAULT_APP_URL).rstrip("/")
    secret = os.environ.get("RELAY_WEBHOOK_SECRET", DEFAULT_SECRET)

    thread_id = args.thread or await newest_thread_id()
    delivery_id = args.delivery_id or f"dlv_{int(time.time() * 1000)}"
    deliveries = (
        [f"{delivery_id}_a", f"{delivery_id}_b"] if args.concurrent else [delivery_id]
    )

    results = await asyncio.gather(
        *[
            asyncio.to_thread(
                send_one, app_url, secret, thread_id, one_id, args.sender, args.text
            )
            for one_id in deliveries
        ]
    )

    for one_id, result in zip(deliveries, results, strict=True):
        print(f"POST /api/webhooks/relay (delivery_id={one_id}) -> {result}")


async def _main() -> None:
    try:
        await run()
    finally:
        await dispose_engine()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
