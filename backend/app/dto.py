"""
DTO types — the shape the API/UI layers consume. Distinct from the table
metadata in ``app/schema.py``. The domain layer is responsible for mapping row
-> DTO; callers above it never see raw DB row shapes.

These mirror ``frontend/src/types/dto.ts`` field-for-field, including its
snake/camel mix. The frontend is a separate codebase that parses this JSON
directly, so the key names here are a contract: renaming one breaks the UI.
That is also why no field carries an alias or a serialization override —
what is written below is exactly what goes on the wire.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

UserRole = Literal["patient", "physician"]

ThreadPriority = Literal["low", "normal", "high"]


class ApiUser(BaseModel):
    id: str
    name: str
    is_physician: bool


class ThreadMetadata(BaseModel):
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


class ApiThread(BaseModel):
    id: str
    title: str
    #: Participant ids. By product rule there is exactly one patient (always
    #: present, always first) and zero-or-more physicians.
    users: list[str]
    date_created: int
    metadata: ThreadMetadata


class ApiMessage(BaseModel):
    id: int
    #: Author id — resolves to either a patient or a physician.
    userId: str
    threadId: str
    message: str
    timestamp: int
    msgIndex: int


# --- Request bodies -------------------------------------------------------
#
# Every endpoint that accepts a body validates it with one of these before the
# domain layer sees it, so a bad shape turns into a 400 with a useful message
# instead of a TypeError somewhere further in. The field names are camelCase
# because they come from the browser client.

#: Trimmed and required to hold something once trimmed.
NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CreateThreadRequest(BaseModel):
    title: NonBlankStr
    userIds: Annotated[list[NonBlankStr], Field(min_length=1)]


class SendMessageRequest(BaseModel):
    userId: NonBlankStr
    message: NonBlankStr


# --- Health -----------------------------------------------------------------


class HealthCounts(BaseModel):
    users: int
    threads: int
    messages_in_first_thread: int


class HealthResponse(BaseModel):
    ok: bool
    counts: HealthCounts
    first_thread: ApiThread | None
    first_message: ApiMessage | None


class HealthWriteResponse(BaseModel):
    ok: bool
    inserted: ApiMessage
