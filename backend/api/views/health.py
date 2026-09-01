"""
Health check plus a lightweight smoke test of the domain layer. Verifies
Django and Postgres are wired together end-to-end without needing a browser.

- ``GET``  — read path (users + threads + a thread's messages).
- ``POST`` — write path (appends a patient-authored message to the first
  thread, exercising the message insert and the author CHECK constraint).
"""

from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.exceptions import error_response
from core.messages import append_message, list_thread_messages
from core.threads import list_threads
from core.users import list_all_users

#: The seeded patient. The demo frontend hardcodes this id too.
DEFAULT_PATIENT_ID = "user1"


class HealthView(APIView):
    def get(self, request: Request) -> Response:
        try:
            users = list_all_users()
            threads = list_threads()
            first_thread = threads[0] if threads else None
            first_messages = (
                list_thread_messages(first_thread["id"]) if first_thread else []
            )
        except Exception as exc:
            return error_response(
                "health_failed", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "ok": True,
                "counts": {
                    "users": len(users),
                    "threads": len(threads),
                    "messages_in_first_thread": len(first_messages),
                },
                "first_thread": first_thread,
                "first_message": first_messages[0] if first_messages else None,
            }
        )

    def post(self, request: Request) -> Response:
        try:
            threads = list_threads()
            if not threads:
                return error_response(
                    "no_threads", "no threads to write to", status.HTTP_404_NOT_FOUND
                )
            target = threads[0]
            patient_id = next(
                (u for u in target["users"] if u == DEFAULT_PATIENT_ID),
                DEFAULT_PATIENT_ID,
            )
            inserted = append_message(
                thread_id=target["id"],
                author_id=patient_id,
                author_role="patient",
                text=f"health POST @ {timezone.now().isoformat()}",
            )
        except Exception as exc:
            return error_response(
                "write_failed", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response({"ok": True, "inserted": inserted})
