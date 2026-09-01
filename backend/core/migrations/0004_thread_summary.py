"""Add threads.summary. Written by the summarize_thread queue job."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_jobs"),
    ]

    operations = [
        migrations.AddField(
            model_name="thread",
            name="summary",
            field=models.TextField(blank=True, null=True),
        ),
    ]
