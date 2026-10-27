"""Baseline persistence mapping; no business workflow is implemented here."""

import sqlalchemy as sa

from app.infrastructure.db.base import Base

jobs_table = sa.Table(
    "jobs",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("actor_id", sa.UUID(), nullable=False),
    sa.Column("conversation_id", sa.UUID(), nullable=False),
    sa.Column("up_to_seq", sa.Integer(), sa.CheckConstraint("up_to_seq >= 0"), nullable=False),
    sa.Column("idempotency_key", sa.String(128), nullable=False),
    sa.Column("request_hash", sa.CHAR(64), nullable=False),
    sa.Column(
        "status",
        sa.String(16),
        sa.CheckConstraint("status IN ('pending','processing','succeeded','partial','failed')"),
        nullable=False,
        server_default=sa.text("'pending'"),
    ),
    sa.Column("reading_intent_id", sa.UUID()),
    sa.Column("recommendation_job_id", sa.UUID()),
    sa.Column("topic_summary", sa.Text()),
    sa.Column(
        "attempts",
        sa.Integer(),
        sa.CheckConstraint("attempts >= 0"),
        nullable=False,
        server_default=sa.text("0"),
    ),
    sa.Column(
        "max_attempts",
        sa.Integer(),
        sa.CheckConstraint("max_attempts BETWEEN 1 AND 10"),
        nullable=False,
        server_default=sa.text("3"),
    ),
    sa.Column("lease_until", sa.DateTime(timezone=True)),
    sa.Column(
        "next_attempt_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    ),
    sa.Column("error_code", sa.String(80)),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column(
        "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column("completed_at", sa.DateTime(timezone=True)),
    sa.UniqueConstraint("actor_id", "idempotency_key"),
    schema="handoff",
)
sa.Index(
    "ix_handoff_queue", jobs_table.c.status, jobs_table.c.next_attempt_at, jobs_table.c.lease_until
)
