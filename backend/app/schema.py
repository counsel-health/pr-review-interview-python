"""
SQLAlchemy Core table metadata.

These are descriptions of the tables the migrations in ``migrations/`` build,
used to compose statements in the domain layer. There are no ORM models and no
mapped classes anywhere in this app.

Two conventions worth knowing before reading further:

* Wall-clock fields the frontend reads (``threads.date_created``,
  ``messages.timestamp``) are epoch **milliseconds** stored as ``BIGINT``, not
  ``timestamptz``. The DTOs hand them to the browser as raw numbers. Purely
  server-side bookkeeping columns (``created_at``, ``visible_after``, ...) are
  real ``timestamptz`` values.
* ``threads.metadata`` holds camelCase keys, because that blob is serialized
  straight through to the browser as ``ThreadMetadata`` (see
  ``frontend/src/types/dto.ts``).
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata_obj = MetaData()

#: Server-side default for ``threads.metadata``. Kept as SQL rather than a
#: Python dict so a row inserted outside the app still gets a complete blob.
DEFAULT_THREAD_METADATA_SQL = """{
  "unrespondedPatientMessagesCount": 0,
  "lastSummaryGenerated": null,
  "topicTags": [],
  "priority": "normal"
}"""

patients = Table(
    "patients",
    metadata_obj,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    # Contact address Relay routes inbound messages by. Nullable: a patient who
    # has never given us a number simply has none on file.
    Column("phone", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Index("patients_phone_idx", "phone", unique=True),
)

physicians = Table(
    "physicians",
    metadata_obj,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

threads = Table(
    "threads",
    metadata_obj,
    Column("id", Text, primary_key=True),
    Column("title", Text, nullable=False),
    # Epoch milliseconds.
    Column("date_created", BigInteger, nullable=False),
    # A thread's patient is fixed for the life of the thread. See app/threads.py.
    Column("patient_id", Text, ForeignKey("patients.id"), nullable=False),
    # Written by the summarize_thread job. Deliberately absent from ApiThread.
    Column("summary", Text, nullable=True),
    # Denormalized, frequently-updated thread state. camelCase keys.
    Column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text(f"'{DEFAULT_THREAD_METADATA_SQL}'::jsonb"),
    ),
    Index("threads_patient_id_idx", "patient_id"),
)

#: The care team on a thread: many physicians, no duplicates.
threads_physicians = Table(
    "threads_physicians",
    metadata_obj,
    Column("thread_id", Text, ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True),
    Column("physician_id", Text, ForeignKey("physicians.id"), primary_key=True),
    Column("added_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # The composite primary key already covers lookups by thread; this covers
    # the other direction, "which threads is this physician on".
    Index("threads_physicians_physician_id_idx", "physician_id"),
)

messages = Table(
    "messages",
    metadata_obj,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("thread_id", Text, ForeignKey("threads.id"), nullable=False),
    # Exactly one of the two author columns is set — see messages_author_xor.
    Column("author_patient_id", Text, ForeignKey("patients.id"), nullable=True),
    Column("author_physician_id", Text, ForeignKey("physicians.id"), nullable=True),
    Column("message", Text, nullable=False),
    # Epoch milliseconds.
    Column("timestamp", BigInteger, nullable=False),
    # Position within the thread, dense and 0-based.
    Column("msg_index", Integer, nullable=False),
    # Relay's delivery id for an inbound message. Messages that did not come in
    # through Relay carry ''.
    Column("provider_message_id", Text, nullable=False, server_default=text("''")),
    # A thread's message ordering is a real invariant, not just a convention:
    # two writers racing to claim the same index must not both succeed.
    UniqueConstraint("thread_id", "msg_index", name="messages_thread_id_msg_index_key"),
    CheckConstraint(
        "(author_patient_id IS NOT NULL) <> (author_physician_id IS NOT NULL)",
        name="messages_author_xor",
    ),
    # thread_id carries no index of its own.
)

#: Backing table for the SQS-shaped job queue in ``app/jobs/queue.py``. The
#: columns exist to honor SQS semantics locally: at-least-once delivery,
#: visibility timeouts, deduplication, and attempt accounting.
jobs = Table(
    "jobs",
    metadata_obj,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("name", Text, nullable=False),
    Column("payload", JSONB, nullable=False),
    # 'queued' | 'in_flight' | 'done' | 'failed'
    Column("status", Text, nullable=False, server_default=text("'queued'")),
    Column("attempts", Integer, nullable=False, server_default=text("0")),
    Column("max_attempts", Integer, nullable=False, server_default=text("5")),
    Column("deduplication_id", Text, nullable=True),
    # Stored for SQS parity. Nothing reads it yet.
    Column("message_group_id", Text, nullable=True),
    Column("receipt_handle", Text, nullable=True),
    # When the job next becomes pollable. Callers push this forward to delay a
    # job; workers push it forward to hold a visibility timeout.
    Column("visible_after", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("last_error", Text, nullable=True),
    # Supports the receive_messages poll, which only ever looks at queued rows.
    Index("jobs_visible_after_idx", "visible_after", postgresql_where=text("status = 'queued'")),
    Index(
        "jobs_dedup_idx",
        "deduplication_id",
        unique=True,
        postgresql_where=text("deduplication_id IS NOT NULL"),
    ),
)
