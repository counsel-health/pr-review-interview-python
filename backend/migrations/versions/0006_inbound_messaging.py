"""Schema for inbound Relay messaging.

A contact address so we can route an inbound SMS to a patient, and a provider
message id on messages so an inbound row can be tied back to Relay's delivery.

Revision ID: 0006
Revises: 0005
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

#: The number Relay has on file for the seeded patient.
SEEDED_PATIENT_PHONE = "+15550000001"


def upgrade() -> None:
    # Patient contact address Relay routes inbound messages by. Added nullable,
    # backfilled for the existing patient, then indexed for the webhook lookup.
    op.add_column("patients", sa.Column("phone", sa.Text(), nullable=True))
    op.get_bind().execute(
        sa.text("UPDATE patients SET phone = :phone WHERE id = 'user1'"),
        {"phone": SEEDED_PATIENT_PHONE},
    )
    op.create_index("patients_phone_idx", "patients", ["phone"], unique=True)

    # Tie each message to Relay's delivery id. Existing messages predate Relay
    # and don't have one, so default them to '' and make the column required.
    op.add_column(
        "messages",
        sa.Column(
            "provider_message_id",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )

    # The webhook looks an inbound message up by Relay's delivery id and the
    # inbox reads a thread's messages newest-first. Both are served by the
    # indexes `messages` already carries, so this migration adds none.


def downgrade() -> None:
    op.drop_column("messages", "provider_message_id")
    op.drop_index("patients_phone_idx", table_name="patients")
    op.drop_column("patients", "phone")
