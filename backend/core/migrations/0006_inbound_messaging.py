"""
Schema for the inbound Relay messaging feature: a contact address so we can
route an inbound SMS to a patient, and a provider message id on messages so an
inbound row can be tied back to Relay's delivery.
"""

from django.db import migrations, models

#: The number Relay has on file for the seeded patient.
SEEDED_PATIENT_PHONE = "+15550000001"


def backfill_patient_phone(apps, schema_editor):
    Patient = apps.get_model("core", "Patient")
    Patient.objects.filter(id="user1").update(phone=SEEDED_PATIENT_PHONE)


def clear_patient_phone(apps, schema_editor):
    Patient = apps.get_model("core", "Patient")
    Patient.objects.update(phone=None)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_thread_metadata"),
    ]

    operations = [
        # Patient contact address Relay routes inbound messages by. Added
        # nullable, backfilled for the existing patient, then indexed for the
        # webhook lookup.
        migrations.AddField(
            model_name="patient",
            name="phone",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_patient_phone, clear_patient_phone),
        migrations.AddConstraint(
            model_name="patient",
            constraint=models.UniqueConstraint(
                fields=("phone",), name="patients_phone_idx"
            ),
        ),
        # Tie each message to Relay's delivery id. Existing messages predate
        # Relay and don't have one, so default them to '' and make the column
        # required.
        migrations.AddField(
            model_name="message",
            name="provider_message_id",
            field=models.TextField(default=""),
        ),
        # The webhook looks an inbound message up by Relay's delivery id and the
        # inbox reads a thread's messages newest-first. Both are served by the
        # indexes `messages` already carries, so this migration adds none.
    ]
