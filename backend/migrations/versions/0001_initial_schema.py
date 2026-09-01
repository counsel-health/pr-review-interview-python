"""Initial schema.

Patients and physicians are separate tables, a thread belongs to exactly one
patient and carries a set of physicians, and a message is authored by exactly
one of the two — enforced by ``messages_author_xor`` rather than by convention.

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "physicians",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "threads",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        # Epoch milliseconds, not a timestamptz: the frontend reads it as a number.
        sa.Column("date_created", sa.BigInteger(), nullable=False),
        sa.Column(
            "patient_id",
            sa.Text(),
            sa.ForeignKey("patients.id", name="threads_patient_id_fkey"),
            nullable=False,
        ),
    )
    op.create_index("threads_patient_id_idx", "threads", ["patient_id"])

    # Many physicians per thread, no duplicates, expressed in the schema.
    op.create_table(
        "threads_physicians",
        sa.Column(
            "thread_id",
            sa.Text(),
            sa.ForeignKey(
                "threads.id", name="threads_physicians_thread_id_fkey", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column(
            "physician_id",
            sa.Text(),
            sa.ForeignKey("physicians.id", name="threads_physicians_physician_id_fkey"),
            nullable=False,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("thread_id", "physician_id"),
    )
    # The primary key already serves lookups by thread; this serves the other
    # direction, "which threads is this physician on".
    op.create_index(
        "threads_physicians_physician_id_idx", "threads_physicians", ["physician_id"]
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "thread_id",
            sa.Text(),
            sa.ForeignKey("threads.id", name="messages_thread_id_fkey"),
            nullable=False,
        ),
        sa.Column(
            "author_patient_id",
            sa.Text(),
            sa.ForeignKey("patients.id", name="messages_author_patient_id_fkey"),
            nullable=True,
        ),
        sa.Column(
            "author_physician_id",
            sa.Text(),
            sa.ForeignKey("physicians.id", name="messages_author_physician_id_fkey"),
            nullable=True,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        # Epoch milliseconds.
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.Column("msg_index", sa.Integer(), nullable=False),
        # A thread's message ordering is a real invariant, not just a
        # convention: two writers racing to claim the same index must not both
        # succeed.
        sa.UniqueConstraint(
            "thread_id", "msg_index", name="messages_thread_id_msg_index_key"
        ),
        sa.CheckConstraint(
            "(author_patient_id IS NOT NULL) <> (author_physician_id IS NOT NULL)",
            name="messages_author_xor",
        ),
    )
    # thread_id carries no index of its own.


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_index("threads_physicians_physician_id_idx", table_name="threads_physicians")
    op.drop_table("threads_physicians")
    op.drop_index("threads_patient_id_idx", table_name="threads")
    op.drop_table("threads")
    op.drop_table("physicians")
    op.drop_table("patients")
