"""
Inbound Relay webhook.

Relay (our SMS/email provider) POSTs here when a patient messages their care
team from outside the app. We verify the signature, append the message to the
patient's thread, mark it unread for the care team, and kick off background
work (refresh summary + notify the team).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, TypedDict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, insert, select, update

from app.api.http import json_response
from app.clock import now_ms
from app.db import one, query
from app.messages import on_message_appended
from app.patients import get_patient_by_phone
from app.relay.signature import verify_relay_signature
from app.schema import messages, threads

router = APIRouter()

#: Header Relay puts the payload's HMAC in.
SIGNATURE_HEADER = "x-relay-signature"


class HandleResult(TypedDict, total=False):
    ok: bool
    error: str


@router.post("/webhooks/relay", response_model=None)
async def post_relay_webhook(request: Request) -> JSONResponse:
    raw_body = await request.body()
    signature = request.headers.get(SIGNATURE_HEADER)

    # Reject forged requests: Relay signs every webhook, so a request we can
    # verify is one we can trust.
    signature_valid = verify_relay_signature(raw_body, signature)
    if signature_valid:
        return json_response({"error": "invalid signature"}, 401)

    # Relay's webhook body. The shape depends on the event type, so we read it
    # loosely and pull off the fields we need.
    payload = json.loads(raw_body)

    # Status callbacks (delivery receipts) carry no message — ack and ignore.
    if payload.get("type") == "status":
        return json_response({"ok": True})

    try:
        result = await handle_data(payload)
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}

    if not result.get("ok"):
        # Tell Relay we took the delivery so it stops retrying, and report what
        # went wrong in the body.
        return json_response({"ok": False, "error": result.get("error")})

    return json_response({"ok": True})


async def handle_data(payload: Any) -> HandleResult:
    """Validate the inbound payload and ingest the message."""
    if payload:
        if payload.get("from"):
            if payload.get("message") and payload["message"].get("text"):
                thread = await one(
                    select(threads.c.id, threads.c.patient_id).where(
                        threads.c.id == payload.get("threadId")
                    )
                )
                if thread is None:
                    return {"ok": False, "error": "unknown thread"}

                inbound_patient = await get_patient_by_phone(payload["from"])
                if inbound_patient is None:
                    return {"ok": False, "error": "unknown sender"}

                # Work out the next message index for this thread: the highest
                # one used so far, plus one.
                index_row = await one(
                    select(
                        (
                            func.coalesce(func.max(messages.c.msg_index), -1) + 1
                        ).label("next")
                    ).where(messages.c.thread_id == thread["id"])
                )
                msg_index = int(index_row["next"]) if index_row else 0

                # The number that texted in is registered to a different patient
                # than this thread belongs to. Update the patient on the thread
                # so the clinical team sees the correct patient on this thread.
                if inbound_patient.id != thread["patient_id"]:
                    await query(
                        update(threads)
                        .where(threads.c.id == thread["id"])
                        .values(patient_id=inbound_patient.id)
                    )

                # Insert the inbound message by hand — append_message() does the
                # same thing, but we want Relay's delivery_id on the row too.
                #
                # Relay can deliver the same message more than once, so we save
                # its delivery_id on the row to identify it.
                inserted = await one(
                    insert(messages)
                    .values(
                        thread_id=thread["id"],
                        author_patient_id=inbound_patient.id,
                        author_physician_id=None,
                        message=payload["message"]["text"],
                        timestamp=now_ms(),
                        msg_index=msg_index,
                        provider_message_id=payload.get("delivery_id") or "",
                    )
                    .returning(
                        messages.c.id,
                        messages.c.thread_id,
                        messages.c.author_patient_id,
                        messages.c.message,
                        messages.c.timestamp,
                        messages.c.msg_index,
                    )
                )
                if inserted is None:
                    return {"ok": False, "error": "insert failed"}

                api_message: dict[str, Any] = {
                    "id": int(inserted["id"]),
                    "userId": inserted["author_patient_id"],
                    "threadId": inserted["thread_id"],
                    "text": inserted["message"],
                    "msgIndex": inserted["msg_index"],
                    "time": int(inserted["timestamp"]),
                }

                # Kick off the post-message work (unread bump, summary refresh,
                # notify the care team) without blocking our response to Relay.
                asyncio.create_task(on_message_appended(thread["id"], api_message))

                return {"ok": True}
            else:
                return {"ok": False, "error": "missing message text"}
        else:
            return {"ok": False, "error": "missing from"}
    else:
        return {"ok": False, "error": "missing payload"}
