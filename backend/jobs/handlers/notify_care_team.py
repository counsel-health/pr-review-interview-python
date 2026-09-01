"""
Job handler: notify a thread's care team that there's a new message.

Delivery goes through the Relay client (``core/relay/client.py``), which is
stubbed to log locally.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict

from core.models import ThreadPhysician
from core.relay.client import send_care_team_notification

NOTIFICATION_BODY = "You have a new message from a patient."


class NotifyCareTeamPayload(TypedDict):
    threadId: str
    messageId: int


class NotificationStrategy(ABC):
    """How a care-team notification gets delivered."""

    @abstractmethod
    def send(self, thread_id: str, physician_id: str, body: str) -> None: ...


class SmsNotificationStrategy(NotificationStrategy):
    def send(self, thread_id: str, physician_id: str, body: str) -> None:
        # Hand off to Relay to deliver the SMS.
        send_care_team_notification(
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


def handle_notify_care_team(payload: Any) -> None:
    strategy = NotificationStrategyFactory.create("sms")

    # Notify every physician on the thread's care team. The queue is
    # at-least-once, so this job can run more than once for the same message.
    physician_ids = ThreadPhysician.objects.filter(
        thread_id=payload["threadId"]
    ).values_list("physician_id", flat=True)

    for physician_id in physician_ids:
        strategy.send(
            thread_id=payload["threadId"],
            physician_id=physician_id,
            body=NOTIFICATION_BODY,
        )
