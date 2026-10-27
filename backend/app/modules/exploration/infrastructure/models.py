"""Baseline persistence mapping; no business workflow is implemented here."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from app.infrastructure.db.base import Base

explorations_table = sa.Table(
    "explorations",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("actor_id", sa.UUID(), nullable=False),
    sa.Column(
        "question_version_id",
        sa.UUID(),
        sa.ForeignKey("content.question_versions.id"),
        nullable=False,
    ),
    sa.Column(
        "status",
        sa.String(16),
        sa.CheckConstraint("status IN ('active','completed','expired')"),
        nullable=False,
        server_default=sa.text("'active'"),
    ),
    sa.Column("current_step_id", sa.String(96)),
    sa.Column("reading_intent_id", sa.UUID()),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column(
        "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("expires_at > created_at"),
    schema="content",
)
sa.Index(
    "ix_explorations_actor", explorations_table.c.actor_id, explorations_table.c.created_at.desc()
)

exploration_answers_table = sa.Table(
    "exploration_answers",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column(
        "exploration_id",
        sa.UUID(),
        sa.ForeignKey("content.explorations.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("step_id", sa.String(96), nullable=False),
    sa.Column("option_id", sa.String(96), nullable=False),
    sa.Column("option_ids", JSONB(none_as_null=True)),
    sa.CheckConstraint(
        "option_ids IS NULL OR (jsonb_typeof(option_ids) = 'array' "
        "AND jsonb_array_length(option_ids) BETWEEN 1 AND 6)",
        name="ck_answer_option_ids",
    ),
    sa.Column("supplementary_text", sa.String(300)),
    sa.Column(
        "submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.UniqueConstraint("exploration_id", "step_id"),
    schema="content",
)
