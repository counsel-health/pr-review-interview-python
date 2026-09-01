"""
Initial schema: patients, physicians, threads, the thread/physician join
table, and messages.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Patient",
            fields=[
                ("id", models.TextField(primary_key=True, serialize=False)),
                ("name", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "patients",
            },
        ),
        migrations.CreateModel(
            name="Physician",
            fields=[
                ("id", models.TextField(primary_key=True, serialize=False)),
                ("name", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "physicians",
            },
        ),
        migrations.CreateModel(
            name="Thread",
            fields=[
                ("id", models.TextField(primary_key=True, serialize=False)),
                ("title", models.TextField()),
                ("date_created", models.BigIntegerField()),
                (
                    "patient",
                    models.ForeignKey(
                        db_column="patient_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="threads",
                        to="core.patient",
                    ),
                ),
            ],
            options={
                "db_table": "threads",
            },
        ),
        migrations.CreateModel(
            name="ThreadPhysician",
            fields=[
                (
                    "pk",
                    models.CompositePrimaryKey(
                        "thread",
                        "physician",
                        blank=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                (
                    "physician",
                    models.ForeignKey(
                        db_column="physician_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="thread_physicians",
                        to="core.physician",
                    ),
                ),
                (
                    "thread",
                    models.ForeignKey(
                        db_column="thread_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="thread_physicians",
                        to="core.thread",
                    ),
                ),
            ],
            options={
                "db_table": "threads_physicians",
            },
        ),
        migrations.AddField(
            model_name="thread",
            name="physicians",
            field=models.ManyToManyField(
                related_name="threads",
                through="core.ThreadPhysician",
                to="core.physician",
            ),
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("message", models.TextField()),
                ("timestamp", models.BigIntegerField()),
                ("msg_index", models.IntegerField()),
                (
                    "author_patient",
                    models.ForeignKey(
                        blank=True,
                        db_column="author_patient_id",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="messages",
                        to="core.patient",
                    ),
                ),
                (
                    "author_physician",
                    models.ForeignKey(
                        blank=True,
                        db_column="author_physician_id",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="messages",
                        to="core.physician",
                    ),
                ),
                (
                    "thread",
                    models.ForeignKey(
                        db_column="thread_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="messages",
                        to="core.thread",
                    ),
                ),
            ],
            options={
                "db_table": "messages",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("thread", "msg_index"),
                        name="messages_thread_id_msg_index_key",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("author_patient__isnull", False),
                            ("author_physician__isnull", False),
                            _connector="XOR",
                        ),
                        name="messages_author_xor",
                    ),
                ],
            },
        ),
    ]
