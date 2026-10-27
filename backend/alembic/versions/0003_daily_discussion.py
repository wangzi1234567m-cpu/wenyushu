"""Multiple reasons and discussion-owned initial context."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_daily_discussion"
down_revision = "0002_daily_exploration"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("exploration_answers", sa.Column("option_ids", JSONB()), schema="content")
    op.create_check_constraint(
        "ck_answer_option_ids",
        "exploration_answers",
        "option_ids IS NULL OR (jsonb_typeof(option_ids) = 'array' AND jsonb_array_length(option_ids) BETWEEN 1 AND 6)",
        schema="content",
    )
    op.execute("CREATE SCHEMA discussion")
    op.create_table(
        "contexts",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False, unique=True),
        sa.Column("exploration_id", sa.UUID()),
        sa.Column("context_json", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("jsonb_typeof(context_json) = 'object'"),
        sa.UniqueConstraint("actor_id", "exploration_id"),
        schema="discussion",
    )


def downgrade():
    op.drop_table("contexts", schema="discussion")
    op.execute("DROP SCHEMA discussion")
    op.drop_constraint("ck_answer_option_ids", "exploration_answers", schema="content")
    op.drop_column("exploration_answers", "option_ids", schema="content")
