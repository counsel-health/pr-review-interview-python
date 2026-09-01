"""
REST endpoints for the messages belonging to a thread.

- ``GET  /api/threads/<thread_id>/messages`` — list messages in order.
- ``POST /api/threads/<thread_id>/messages`` — append a message from a user.

The POST returns the inserted message as a bare ``ApiMessage`` object, not
wrapped in an envelope: the frontend client assigns the response straight into
its message list.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.exceptions import error_response
from api.serializers import SendMessageSerializer
from core.messages import list_thread_messages, send_message


class ThreadMessagesView(APIView):
    def get(self, request: Request, thread_id: str) -> Response:
        try:
            messages = list_thread_messages(thread_id)
        except Exception as exc:
            return error_response(
                "messages_failed", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response(messages)

    def post(self, request: Request, thread_id: str) -> Response:
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        try:
            inserted = send_message(thread_id, payload["userId"], payload["message"])
        except Exception as exc:
            return error_response(
                "send_message_failed", str(exc), status.HTTP_400_BAD_REQUEST
            )
        return Response(inserted, status=status.HTTP_201_CREATED)
