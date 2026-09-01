"""
Request validation for the write endpoints.

Every endpoint that accepts a body validates it with a serializer before the
domain layer sees it, so shape errors turn into a 400 with a useful message
instead of a TypeError somewhere further in. The request field names are
camelCase because they come from the browser client.
"""

from __future__ import annotations

from rest_framework import serializers


class CreateThreadSerializer(serializers.Serializer):
    title = serializers.CharField(allow_blank=False, trim_whitespace=True)
    userIds = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        allow_empty=False,
    )


class SendMessageSerializer(serializers.Serializer):
    userId = serializers.CharField(allow_blank=False)
    message = serializers.CharField(allow_blank=False, trim_whitespace=True)
