"""
Inbound Relay webhook.

Relay (our SMS/email provider) POSTs here when a patient messages their care
team from outside the app. We verify the signature, append the message to the
patient's thread, mark it unread for the care team, and kick off background work
(refresh summary + notify the team).
"""

from __future__ import annotations

import json
import threading
from typing import Any, TypedDict

from django.db.models import Max
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.clock import now_ms
from core.messages import on_message_appended
from core.models import Message, Thread
from core.patients import get_patient_by_phone
from core.relay.signature import verify_relay_signature

#: Header Relay puts the payload's HMAC in.
SIGNATURE_HEADER = "X-Relay-Signature"


class HandleResult(TypedDict, total=False):
    ok: bool
    error: str


class RelayWebhookView(APIView):
    def post(self, request: Request) -> Response:
        raw_body = request.body
        signature = request.headers.get(SIGNATURE_HEADER)

        # Reject forged requests: Relay signs every webhook, so a request we can
        # verify is one we can trust.
        signature_valid = verify_relay_signature(raw_body, signature)
        if signature_valid:
            return Response(
                {"error": "invalid signature"}, status=status.HTTP_401_UNAUTHORIZED
            )

        # Relay's webhook body. The shape depends on the event type, so we read
        # it loosely and pull off the fields we need.
        payload = json.loads(raw_body)

        # Status callbacks (delivery receipts) carry no message — ack and ignore.
        if payload.get("type") == "status":
            return Response({"ok": True})

        try:
            result = handle_data(payload)
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}

        if not result.get("ok"):
            # Tell Relay we took the delivery so it stops retrying, and report
            # what went wrong in the body.
            return Response({"ok": False, "error": result.get("error")})

        return Response({"ok": True})


def handle_data(payload: Any) -> HandleResult:
    """Validate the inbound payload and ingest the message."""
    if payload:
        if payload.get("from"):
            if payload.get("message") and payload["message"].get("text"):
                thread = Thread.objects.filter(id=payload.get("threadId")).first()
                if thread is None:
                    return {"ok": False, "error": "unknown thread"}

                inbound_patient = get_patient_by_phone(payload["from"])
                if inbound_patient is None:
                    return {"ok": False, "error": "unknown sender"}

                # Work out the next message index for this thread: the highest
                # one used so far, plus one.
                highest = Message.objects.filter(thread_id=thread.id).aggregate(
                    highest=Max("msg_index")
                )["highest"]
                msg_index = 0 if highest is None else highest + 1

                # The number that texted in is registered to a different patient
                # than this thread belongs to. Update the patient on the thread
                # so the clinical team sees the correct patient on this thread.
                if inbound_patient["id"] != thread.patient_id:
                    thread.patient_id = inbound_patient["id"]
                    thread.save(update_fields=["patient"])

                # Insert the inbound message by hand — append_message() does the
                # same thing, but we want Relay's delivery_id on the row too.
                # Relay can deliver the same message more than once, so we save
                # its delivery_id on the row to identify it.
                inserted = Message.objects.create(
                    thread_id=thread.id,
                    author_patient_id=inbound_patient["id"],
                    author_physician_id=None,
                    message=payload["message"]["text"],
                    timestamp=now_ms(),
                    msg_index=msg_index,
                    provider_message_id=payload.get("delivery_id") or "",
                )

                api_message: dict[str, Any] = {
                    "id": inserted.id,
                    "userId": inserted.author_patient_id,
                    "threadId": inserted.thread_id,
                    "text": inserted.message,
                    "msgIndex": inserted.msg_index,
                    "time": inserted.timestamp,
                }

                # Kick off the post-message work (unread bump, summary refresh,
                # notify the care team) without blocking our response to Relay.
                threading.Thread(
                    target=on_message_appended,
                    args=(thread.id, api_message),
                    daemon=True,
                ).start()

                return {"ok": True}
            else:
                return {"ok": False, "error": "missing message text"}
        else:
            return {"ok": False, "error": "missing from"}
    else:
        return {"ok": False, "error": "missing payload"}
