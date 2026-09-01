"""
REST endpoint for users.

- ``GET /api/users`` — every patient and physician as a flat ``ApiUser`` list.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.exceptions import error_response
from core.users import list_all_users


class UsersView(APIView):
    def get(self, request: Request) -> Response:
        try:
            users = list_all_users()
        except Exception as exc:
            return error_response(
                "users_failed", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response(users)
