"""
Job handler: notify a thread's care team that there's a new message.

Delivery goes through the Relay client (``app/relay/client.py``), which is
stubbed to log locally.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict

from sqlalchemy import select

from app.db import query
from app.relay.client import send_care_team_notification
from app.schema import threads_physicians

NOTIFICATION_BODY = "You have a new message from a patient."


class NotifyCareTeamPayload(TypedDict):
    threadId: str
    messageId: int


class NotificationStrategy(ABC):
    """How a care-team notification gets delivered."""

    @abstractmethod
    async def send(self, thread_id: str, physician_id: str, body: str) -> None: ...


class SmsNotificationStrategy(NotificationStrategy):
    async def send(self, thread_id: str, physician_id: str, body: str) -> None:
        # Hand off to Relay to deliver the SMS.
        await send_care_team_notification(
            thread_id=thread_id,
            physician_id=physician_id,
            body=body,
        )


class NotificationStrategyFactory:
    """Resolves a delivery channel to the strategy that implements it."""

    @staticmethod
    def create(channel: str) -> NotificationStrategy:
        match channel:
            case "sms":
                return SmsNotificationStrategy()
            case _:
                return SmsNotificationStrategy()


async def handle_notify_care_team(payload: Any) -> None:
    strategy = NotificationStrategyFactory.create("sms")

    # Notify every physician on the thread's care team. The queue is
    # at-least-once, so this job can run more than once for the same message.
    result = await query(
        select(threads_physicians.c.physician_id).where(
            threads_physicians.c.thread_id == payload["threadId"]
        )
    )

    for row in result.rows:
        await strategy.send(
            thread_id=payload["threadId"],
            physician_id=row["physician_id"],
            body=NOTIFICATION_BODY,
        )
