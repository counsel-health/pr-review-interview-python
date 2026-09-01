"""Backing table for the SQS-shaped job queue.

Modeled on the columns needed to honor SQS semantics locally: at-least-once
delivery, visibility timeouts, dedup, and attempt accounting. See
``app/jobs/queue.py``.

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        # 'queued' | 'in_flight' | 'done' | 'failed'
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'queued'")
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "max_attempts", sa.Integer(), nullable=False, server_default=sa.text("5")
        ),
        sa.Column("deduplication_id", sa.Text(), nullable=True),
        # Stored for SQS parity. Nothing reads it yet.
        sa.Column("message_group_id", sa.Text(), nullable=True),
        sa.Column("receipt_handle", sa.Text(), nullable=True),
        sa.Column(
            "visible_after",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
    )

    # Supports the receive_messages poll, which only ever looks at queued rows.
    op.create_index(
        "jobs_visible_after_idx",
        "jobs",
        ["visible_after"],
        postgresql_where=sa.text("status = 'queued'"),
    )
    op.create_index(
        "jobs_dedup_idx",
        "jobs",
        ["deduplication_id"],
        unique=True,
        postgresql_where=sa.text("deduplication_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("jobs_dedup_idx", table_name="jobs")
    op.drop_index("jobs_visible_after_idx", table_name="jobs")
    op.drop_table("jobs")
