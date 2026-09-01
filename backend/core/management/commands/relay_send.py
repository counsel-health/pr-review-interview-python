"""
Simulate an inbound Relay webhook against the locally-running app.

Signs a sample payload with ``RELAY_WEBHOOK_SECRET`` and POSTs it to
``/api/webhooks/relay``, so the whole inbound flow can be exercised offline.

    manage.py relay_send                        # one inbound to the newest thread
    manage.py relay_send --thread <id>          # target a specific thread
    manage.py relay_send --from +15550000004    # spoof a different patient's number
    manage.py relay_send --text "hello"         # custom body
    manage.py relay_send --delivery-id dlv_1    # fixed delivery id (re-send)
    manage.py relay_send --concurrent           # fire two deliveries at once
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from core.models import Thread
from core.relay.signature import sign_relay_payload

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
        return f"connection failed ({exc.reason}); is `manage.py runserver` up?"


class Command(BaseCommand):
    help = "POST a signed sample Relay webhook at the local app."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--thread", default="", help="thread id to deliver to")
        parser.add_argument("--from", dest="sender", default=DEFAULT_FROM)
        parser.add_argument("--text", default=DEFAULT_TEXT)
        parser.add_argument("--delivery-id", dest="delivery_id", default="")
        parser.add_argument("--concurrent", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        app_url = os.environ.get("APP_URL", DEFAULT_APP_URL).rstrip("/")
        secret = os.environ.get("RELAY_WEBHOOK_SECRET", DEFAULT_SECRET)

        thread_id = options["thread"] or self._newest_thread_id()
        delivery_id = options["delivery_id"] or f"dlv_{int(time.time() * 1000)}"

        if options["concurrent"]:
            deliveries = [f"{delivery_id}_a", f"{delivery_id}_b"]
        else:
            deliveries = [delivery_id]

        results: dict[str, str] = {}

        def deliver(one_id: str) -> None:
            results[one_id] = send_one(
                app_url,
                secret,
                thread_id,
                one_id,
                options["sender"],
                options["text"],
            )

        workers = [threading.Thread(target=deliver, args=(d,)) for d in deliveries]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        for one_id in deliveries:
            self.stdout.write(
                f"POST /api/webhooks/relay (delivery_id={one_id}) -> "
                f"{results.get(one_id, 'no response')}"
            )

    def _newest_thread_id(self) -> str:
        thread_id = (
            Thread.objects.order_by("-date_created")
            .values_list("id", flat=True)
            .first()
        )
        if thread_id is None:
            raise CommandError(
                "no threads in the database; run `manage.py migrate` to seed"
            )
        return thread_id
