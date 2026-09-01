"""
Backing table for the SQS-shaped job queue in ``jobs/queue.py``.

The two partial indexes are the ones the queue's hot paths need: polling only
ever scans queued rows, and deduplication only applies to jobs that carry a
``deduplication_id``.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_seed_data"),
    ]

    operations = [
        migrations.CreateModel(
            name="Job",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("name", models.TextField()),
                ("payload", models.JSONField()),
                (
                    "status",
                    models.TextField(
                        choices=[
                            ("queued", "Queued"),
                            ("in_flight", "In Flight"),
                            ("done", "Done"),
                            ("failed", "Failed"),
                        ],
                        default="queued",
                    ),
                ),
                ("attempts", models.IntegerField(default=0)),
                ("max_attempts", models.IntegerField(default=5)),
                ("deduplication_id", models.TextField(blank=True, null=True)),
                ("message_group_id", models.TextField(blank=True, null=True)),
                ("receipt_handle", models.TextField(blank=True, null=True)),
                (
                    "visible_after",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_error", models.TextField(blank=True, null=True)),
            ],
            options={
                "db_table": "jobs",
                "indexes": [
                    models.Index(
                        condition=models.Q(("status", "queued")),
                        fields=["visible_after"],
                        name="jobs_visible_after_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("deduplication_id__isnull", False)),
                        fields=("deduplication_id",),
                        name="jobs_dedup_idx",
                    )
                ],
            },
        ),
    ]
