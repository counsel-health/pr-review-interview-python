"""
Database models.

Two conventions worth knowing before reading further:

* Every table has an explicit ``db_table``/``db_column`` so the generated SQL
  matches the schema by name rather than by Django's derivation rules.
* Wall-clock fields that the frontend reads (``Thread.date_created``,
  ``Message.timestamp``) are epoch **milliseconds** stored as ``BIGINT``, not
  ``timestamptz``. The DTOs hand them to the browser as raw numbers. Purely
  server-side bookkeeping columns (``created_at``, ``visible_after``, ...) are
  real ``timestamptz`` values.
"""

from __future__ import annotations

from typing import Any

from django.db import models
from django.utils import timezone


def default_thread_metadata() -> dict[str, Any]:
    """
    Default value for :attr:`Thread.metadata`.

    The keys are camelCase because this blob is serialized straight through to
    the browser as ``ThreadMetadata`` (see frontend/src/types/dto.ts).
    """
    return {
        "unrespondedPatientMessagesCount": 0,
        "lastSummaryGenerated": None,
        "topicTags": [],
        "priority": "normal",
    }


class Patient(models.Model):
    id = models.TextField(primary_key=True)
    name = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "patients"

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"


class Physician(models.Model):
    id = models.TextField(primary_key=True)
    name = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "physicians"

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"


class Thread(models.Model):
    id = models.TextField(primary_key=True)
    title = models.TextField()
    #: Epoch milliseconds.
    date_created = models.BigIntegerField()
    #: A thread's patient is fixed for the life of the thread. See core/threads.py.
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        db_column="patient_id",
        related_name="threads",
    )
    physicians = models.ManyToManyField(
        Physician,
        through="ThreadPhysician",
        related_name="threads",
    )
    #: Written by the summarize_thread job. Deliberately absent from ApiThread.
    summary = models.TextField(null=True, blank=True)
    #: Denormalized, frequently-updated thread state. camelCase keys.
    metadata = models.JSONField(default=default_thread_metadata)

    class Meta:
        db_table = "threads"

    def __str__(self) -> str:
        return f"{self.title} ({self.id})"


class ThreadPhysician(models.Model):
    """The care team on a thread: many physicians, no duplicates."""

    pk = models.CompositePrimaryKey("thread", "physician")
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        db_column="thread_id",
        related_name="thread_physicians",
    )
    physician = models.ForeignKey(
        Physician,
        on_delete=models.PROTECT,
        db_column="physician_id",
        related_name="thread_physicians",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Both columns are foreign keys, so Django already indexes each of
        # them; the composite primary key covers lookups by thread.
        db_table = "threads_physicians"

    def __str__(self) -> str:
        return f"{self.thread_id} <- {self.physician_id}"


class Message(models.Model):
    id = models.BigAutoField(primary_key=True)
    thread = models.ForeignKey(
        Thread,
        on_delete=models.PROTECT,
        db_column="thread_id",
        related_name="messages",
    )
    #: Exactly one of author_patient / author_physician is set — see the
    #: messages_author_xor constraint below.
    author_patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        db_column="author_patient_id",
        null=True,
        blank=True,
        related_name="messages",
    )
    author_physician = models.ForeignKey(
        Physician,
        on_delete=models.PROTECT,
        db_column="author_physician_id",
        null=True,
        blank=True,
        related_name="messages",
    )
    message = models.TextField()
    #: Epoch milliseconds.
    timestamp = models.BigIntegerField()
    #: Position within the thread, dense and 0-based.
    msg_index = models.IntegerField()

    class Meta:
        db_table = "messages"
        constraints = [
            # A thread's message ordering is a real invariant, not just a
            # convention: two writers racing to claim the same index must not
            # both succeed.
            models.UniqueConstraint(
                fields=["thread", "msg_index"],
                name="messages_thread_id_msg_index_key",
            ),
            models.CheckConstraint(
                condition=models.Q(author_patient__isnull=False)
                ^ models.Q(author_physician__isnull=False),
                name="messages_author_xor",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.thread_id}#{self.msg_index}"


class Job(models.Model):
    """
    Backing table for the SQS-shaped job queue in ``jobs/queue.py``.

    The columns exist to honor SQS semantics locally: at-least-once delivery,
    visibility timeouts, deduplication, and attempt accounting.
    """

    class Status(models.TextChoices):
        QUEUED = "queued"
        IN_FLIGHT = "in_flight"
        DONE = "done"
        FAILED = "failed"

    id = models.BigAutoField(primary_key=True)
    name = models.TextField()
    payload = models.JSONField()
    status = models.TextField(choices=Status.choices, default=Status.QUEUED)
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)
    deduplication_id = models.TextField(null=True, blank=True)
    message_group_id = models.TextField(null=True, blank=True)
    receipt_handle = models.TextField(null=True, blank=True)
    #: When the job next becomes pollable. Callers push this forward to delay a
    #: job; workers push it forward to hold a visibility timeout. Unlike the
    #: other timestamps here it is set explicitly, so it can't use auto_now_add.
    visible_after = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_error = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "jobs"
        indexes = [
            # Supports the receive_messages poll, which only ever looks at
            # queued rows.
            models.Index(
                fields=["visible_after"],
                name="jobs_visible_after_idx",
                condition=models.Q(status="queued"),
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["deduplication_id"],
                name="jobs_dedup_idx",
                condition=models.Q(deduplication_id__isnull=False),
            ),
        ]

    def __str__(self) -> str:
        return f"job {self.id} {self.name} [{self.status}]"
