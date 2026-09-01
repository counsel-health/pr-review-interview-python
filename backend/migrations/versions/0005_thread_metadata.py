"""Add ``threads.metadata``.

A JSONB blob for frequently-updated, denormalized thread state that doesn't
(yet) warrant its own column. Shape::

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
running for a while:

* unrespondedPatientMessagesCount = patient messages sent after the last
  physician reply (i.e. what's currently awaiting a physician).
* lastSummaryGenerated = latest message timestamp when a summary exists.
* topicTags = a small, realistic tag set assigned round-robin.
* priority = derived from the unresponded backlog.

Revision ID: 0005
Revises: 0004
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

DEFAULT_METADATA = """{
  "unrespondedPatientMessagesCount": 0,
  "lastSummaryGenerated": null,
  "topicTags": [],
  "priority": "normal"
}"""

BACKFILL = """
UPDATE threads t
SET metadata = jsonb_build_object(
  'unrespondedPatientMessagesCount', COALESCE(u.cnt, 0),
  'lastSummaryGenerated',
    CASE WHEN t.summary IS NOT NULL THEN to_jsonb(lm.last_ts)
         ELSE 'null'::jsonb END,
  'topicTags',
    CASE (r.rn % 4)
      WHEN 0 THEN '["general", "follow-up"]'::jsonb
      WHEN 1 THEN '["medication", "side-effects"]'::jsonb
      WHEN 2 THEN '["lab-results", "urgent"]'::jsonb
      ELSE        '["lifestyle", "nutrition"]'::jsonb
    END,
  'priority',
    CASE
      WHEN COALESCE(u.cnt, 0) >= 3 THEN 'high'
      WHEN COALESCE(u.cnt, 0) >= 1 THEN 'normal'
      ELSE 'low'
    END
)
FROM (
  SELECT id, ROW_NUMBER() OVER (ORDER BY date_created) AS rn FROM threads
) r
LEFT JOIN (
  SELECT t2.id AS thread_id,
         COUNT(m.id) FILTER (
           WHERE m.author_patient_id IS NOT NULL
             AND m.msg_index > COALESCE(lp.last_phys_index, -1)
         ) AS cnt
  FROM threads t2
  LEFT JOIN (
    SELECT thread_id, MAX(msg_index) AS last_phys_index
    FROM messages
    WHERE author_physician_id IS NOT NULL
    GROUP BY thread_id
  ) lp ON lp.thread_id = t2.id
  LEFT JOIN messages m ON m.thread_id = t2.id
  GROUP BY t2.id
) u ON u.thread_id = r.id
LEFT JOIN (
  SELECT thread_id, MAX(timestamp) AS last_ts
  FROM messages
  GROUP BY thread_id
) lm ON lm.thread_id = r.id
WHERE t.id = r.id
"""


def upgrade() -> None:
    op.add_column(
        "threads",
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text(f"'{DEFAULT_METADATA}'::jsonb"),
        ),
    )
    op.get_bind().execute(sa.text(BACKFILL))


def downgrade() -> None:
    op.drop_column("threads", "metadata")
