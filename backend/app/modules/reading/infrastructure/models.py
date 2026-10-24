"""Baseline persistence mapping; no business workflow is implemented here."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from app.infrastructure.db.base import Base

intents_table = sa.Table(
    "intents",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("actor_id", sa.UUID(), nullable=False),
    sa.Column(
        "source_type",
        sa.String(24),
        sa.CheckConstraint("source_type IN ('daily_question','direct_search','discussion')"),
        nullable=False,
    ),
    sa.Column("source_ref_id", sa.UUID()),
    sa.Column(
        "purpose",
        sa.String(24),
        sa.CheckConstraint("purpose IN ('interest','learning','exploration')"),
        nullable=False,
    ),
    sa.Column("central_question", sa.Text()),
    sa.Column(
        "topics",
        JSONB(),
        sa.CheckConstraint("jsonb_typeof(topics) = 'array'"),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    ),
    sa.Column("focus", sa.Text()),
    sa.Column(
        "preferences",
        JSONB(),
        sa.CheckConstraint("jsonb_typeof(preferences) = 'object'"),
        nullable=False,
    ),
    sa.Column(
        "schema_version",
        sa.Integer(),
        sa.CheckConstraint("schema_version >= 1"),
        nullable=False,
        server_default=sa.text("1"),
    ),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column("expires_at", sa.DateTime(timezone=True)),
    schema="reading",
)
sa.Index("ix_intents_actor", intents_table.c.actor_id, intents_table.c.created_at.desc())

recommendation_jobs_table = sa.Table(
    "recommendation_jobs",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("actor_id", sa.UUID(), nullable=False),
    sa.Column("reading_intent_id", sa.UUID(), sa.ForeignKey("reading.intents.id"), nullable=False),
    sa.Column("idempotency_key", sa.String(128), nullable=False),
    sa.Column("request_hash", sa.CHAR(64), nullable=False),
    sa.Column(
        "requested_limit",
        sa.Integer(),
        sa.CheckConstraint("requested_limit BETWEEN 1 AND 3"),
        nullable=False,
        server_default=sa.text("3"),
    ),
    sa.Column(
        "status",
        sa.String(16),
        sa.CheckConstraint("status IN ('pending','processing','succeeded','partial','failed')"),
        nullable=False,
        server_default=sa.text("'pending'"),
    ),
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
    sa.Column("error_message", sa.Text()),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column(
        "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column("completed_at", sa.DateTime(timezone=True)),
    sa.UniqueConstraint("actor_id", "idempotency_key"),
    schema="reading",
)
sa.Index(
    "ix_recommendation_jobs_queue",
    recommendation_jobs_table.c.status,
    recommendation_jobs_table.c.next_attempt_at,
    recommendation_jobs_table.c.lease_until,
)

recommendation_items_table = sa.Table(
    "recommendation_items",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column(
        "job_id",
        sa.UUID(),
        sa.ForeignKey("reading.recommendation_jobs.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("work_id", sa.UUID(), nullable=False),
    sa.Column("rank", sa.Integer(), sa.CheckConstraint("rank BETWEEN 1 AND 3"), nullable=False),
    sa.Column("title", sa.String(400), nullable=False),
    sa.Column("author", sa.String(300), nullable=False),
    sa.Column("summary", sa.Text(), nullable=False),
    sa.Column("recommendation_reason", sa.Text(), nullable=False),
    sa.Column(
        "verification_status",
        sa.String(20),
        sa.CheckConstraint("verification_status IN ('verified')"),
        nullable=False,
    ),
    sa.Column(
        "evidence_urls",
        JSONB(),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_urls) = 'array' AND jsonb_array_length(evidence_urls) >= 1"
        ),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    ),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.UniqueConstraint("job_id", "rank"),
    sa.UniqueConstraint("job_id", "work_id"),
    schema="reading",
)
