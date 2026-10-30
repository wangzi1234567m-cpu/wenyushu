"""Private discussion viewpoints and on-demand extraction cache."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004_saved_viewpoints"
down_revision = "0003_daily_discussion"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "viewpoint_extractions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("up_to_seq", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("lease_id", sa.UUID()),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("items", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("up_to_seq >= 1"),
        sa.CheckConstraint("attempts BETWEEN 1 AND 3"),
        sa.CheckConstraint("status IN ('processing','succeeded','failed')"),
        sa.CheckConstraint("jsonb_typeof(items) = 'array' AND jsonb_array_length(items) <= 3"),
        sa.UniqueConstraint("actor_id", "conversation_id", "up_to_seq"),
        schema="discussion",
    )
    op.create_table(
        "saved_viewpoints",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID()),
        sa.Column("source_message_ids", JSONB(), nullable=False),
        sa.Column("source_type", sa.String(24), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("topic_title", sa.String(300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source_type IN ('user_quote','ai_viewpoint','ai_summary')"),
        sa.CheckConstraint("char_length(content) BETWEEN 1 AND 16000"),
        sa.CheckConstraint(
            "jsonb_typeof(source_message_ids) = 'array' AND jsonb_array_length(source_message_ids) BETWEEN 1 AND 4"
        ),
        schema="discussion",
    )
    op.create_index(
        "ix_saved_viewpoints_actor",
        "saved_viewpoints",
        ["actor_id", "created_at", "id"],
        schema="discussion",
    )


def downgrade():
    op.drop_table("saved_viewpoints", schema="discussion")
    op.drop_table("viewpoint_extractions", schema="discussion")
