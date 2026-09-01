"""
DTO types — the shape the API/UI layers consume. Distinct from the ORM models
in ``core/models.py``. The domain layer is responsible for mapping model row →
DTO; callers above it never see raw model instances.

These mirror ``frontend/src/types/dto.ts`` field-for-field, including its
snake/camel mix. The frontend is a separate codebase that parses this JSON
directly, so the key names here are a contract: renaming one breaks the UI.
"""

from __future__ import annotations

from typing import Literal, TypedDict


class ApiUser(TypedDict):
    id: str
    name: str
    is_physician: bool


ThreadPriority = Literal["low", "normal", "high"]

UserRole = Literal["patient", "physician"]


class ThreadMetadata(TypedDict):
    """
    Frequently-updated, denormalized thread state stored in the
    ``threads.metadata`` JSONB column.
    """

    #: Patient messages awaiting a physician reply. Incremented when a patient
    #: sends a message and reset to 0 when a physician responds in the thread.
    unrespondedPatientMessagesCount: int
    #: Epoch ms of the last summary the queue job produced, or None if never.
    lastSummaryGenerated: int | None
    topicTags: list[str]
    priority: ThreadPriority


class ApiThread(TypedDict):
    id: str
    title: str
    #: Participant ids. By product rule there is exactly one patient (always
    #: present, always first) and zero-or-more physicians.
    users: list[str]
    date_created: int
    metadata: ThreadMetadata


class ApiMessage(TypedDict):
    id: int
    #: Author id — resolves to either a patient or a physician.
    userId: str
    threadId: str
    message: str
    timestamp: int
    msgIndex: int
