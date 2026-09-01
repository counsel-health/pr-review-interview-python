"""
Read endpoint for the upcoming mobile client.

- ``GET /api/inbox?physicianId=...`` — the threads on a care team member's
  plate, each with its messages, so the app can render an inbox in one call.
"""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.exceptions import error_response
from core.models import Message, Thread


class InboxView(APIView):
    def get(self, request: Request) -> Response:
        # Whose inbox to load — the mobile client tells us which physician.
        physician_id = request.query_params.get("physicianId")
        if not physician_id:
            return error_response(
                "invalid_request",
                "physicianId is required",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Every thread this physician is on.
            threads = list(
                Thread.objects.filter(thread_physicians__physician_id=physician_id)
                .order_by("-date_created")
                .values("id", "title", "patient_id", "metadata")
            )

            inbox: list[dict[str, Any]] = []
            for thread in threads:
                # Load every message in this thread (one query per thread).
                messages = list(
                    Message.objects.filter(thread_id=thread["id"])
                    .order_by("-timestamp")
                    .values(
                        "id",
                        "thread_id",
                        "author_patient_id",
                        "author_physician_id",
                        "message",
                        "timestamp",
                        "msg_index",
                    )
                )
                inbox.append({**thread, "messages": messages})
        except Exception as exc:
            return error_response(
                "inbox_failed", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response(inbox)
