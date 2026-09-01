"""
Add ``threads.metadata``: a JSONB blob for frequently-updated, denormalized
thread state that doesn't (yet) warrant its own column.

    {
      "unrespondedPatientMessagesCount": int,       # +1 on a patient message,
                                                    # reset to 0 on a physician reply
      "lastSummaryGenerated":            int|null,  # epoch ms, bumped by the
                                                    # summarize_thread job
      "topicTags":                       [str],     # free-form thread tags
      "priority":                        str        # 'low' | 'normal' | 'high'
    }

Existing threads are backfilled from their real message history rather than
left on the default, so the seeded data looks like a system that has been
running for a while.
"""

from django.db import migrations, models

import core.models

#: Assigned round-robin so the seeded threads have a plausible spread of tags.
TAG_SETS = [
    ["general", "follow-up"],
    ["medication", "side-effects"],
    ["lab-results", "urgent"],
    ["lifestyle", "nutrition"],
]


def backfill_metadata(apps, schema_editor):
    Thread = apps.get_model("core", "Thread")
    Message = apps.get_model("core", "Message")

    # Highest msg_index a physician has replied at, per thread. Patient
    # messages after this point are what's still awaiting a reply.
    last_physician_index = dict(
        Message.objects.filter(author_physician__isnull=False)
        .values("thread_id")
        .annotate(last_index=models.Max("msg_index"))
        .values_list("thread_id", "last_index")
    )
    last_message_timestamp = dict(
        Message.objects.values("thread_id")
        .annotate(last_ts=models.Max("timestamp"))
        .values_list("thread_id", "last_ts")
    )

    unresponded: dict[str, int] = {}
    patient_messages = Message.objects.filter(author_patient__isnull=False).values_list(
        "thread_id", "msg_index"
    )
    for thread_id, msg_index in patient_messages.iterator(chunk_size=5000):
        if msg_index > last_physician_index.get(thread_id, -1):
            unresponded[thread_id] = unresponded.get(thread_id, 0) + 1

    threads = list(Thread.objects.order_by("date_created"))
    for position, thread in enumerate(threads, start=1):
        count = unresponded.get(thread.id, 0)
        if count >= 3:
            priority = "high"
        elif count >= 1:
            priority = "normal"
        else:
            priority = "low"
        thread.metadata = {
            "unrespondedPatientMessagesCount": count,
            "lastSummaryGenerated": (
                last_message_timestamp.get(thread.id) if thread.summary is not None else None
            ),
            "topicTags": list(TAG_SETS[position % len(TAG_SETS)]),
            "priority": priority,
        }

    Thread.objects.bulk_update(threads, ["metadata"], batch_size=500)


def reset_metadata(apps, schema_editor):
    Thread = apps.get_model("core", "Thread")
    Thread.objects.update(metadata=core.models.default_thread_metadata())


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_thread_summary"),
    ]

    operations = [
        migrations.AddField(
            model_name="thread",
            name="metadata",
            field=models.JSONField(default=core.models.default_thread_metadata),
        ),
        migrations.RunPython(backfill_metadata, reset_metadata),
    ]
