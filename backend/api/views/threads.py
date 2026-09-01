"""
REST endpoints for threads.

- ``GET  /api/threads?query=...`` — list threads, optionally filtered.
- ``POST /api/threads``           — create a thread from a list of user ids.

Thin wrappers around the domain layer in ``core/``.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.exceptions import error_response
from api.serializers import CreateThreadSerializer
from core.threads import create_thread, list_threads


class ThreadsView(APIView):
    def get(self, request: Request) -> Response:
        try:
            threads = list_threads(request.query_params.get("query"))
        except Exception as exc:
            return error_response(
                "threads_failed", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response(threads)

    def post(self, request: Request) -> Response:
        serializer = CreateThreadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        try:
            thread = create_thread(payload["title"], payload["userIds"])
        except Exception as exc:
            # Anything the domain layer rejects (an unknown user id, more than
            # one patient) is a bad request, not a server fault.
            return error_response(
                "create_thread_failed", str(exc), status.HTTP_400_BAD_REQUEST
            )
        return Response(thread, status=status.HTTP_201_CREATED)
