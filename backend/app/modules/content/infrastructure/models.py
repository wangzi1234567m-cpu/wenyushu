"""Baseline persistence mapping; no business workflow is implemented here."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from app.infrastructure.db.base import Base

topics_table = sa.Table(
    "topics",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("slug", sa.String(96), nullable=False, unique=True),
    sa.Column("title", sa.String(200), nullable=False),
    sa.Column("description", sa.Text()),
    sa.Column(
        "audience",
        sa.String(24),
        sa.CheckConstraint("audience IN ('adult','teen','child','all')"),
        nullable=False,
        server_default=sa.text("'adult'"),
    ),
    sa.Column(
        "status",
        sa.String(16),
        sa.CheckConstraint("status IN ('draft','published','archived')"),
        nullable=False,
        server_default=sa.text("'draft'"),
    ),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    schema="content",
)

questions_table = sa.Table(
    "questions",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("topic_id", sa.UUID(), sa.ForeignKey("content.topics.id"), nullable=False),
    sa.Column("slug", sa.String(96), nullable=False, unique=True),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    schema="content",
)

question_versions_table = sa.Table(
    "question_versions",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("question_id", sa.UUID(), sa.ForeignKey("content.questions.id"), nullable=False),
    sa.Column("version", sa.Integer(), sa.CheckConstraint("version >= 1"), nullable=False),
    sa.Column("title", sa.String(300), nullable=False),
    sa.Column("intro", sa.Text(), nullable=False),
    sa.Column(
        "flow_json",
        JSONB(),
        sa.CheckConstraint("jsonb_typeof(flow_json) = 'object'"),
        nullable=False,
    ),
    sa.Column(
        "status",
        sa.String(16),
        sa.CheckConstraint("status IN ('draft','reviewed','published','archived')"),
        nullable=False,
        server_default=sa.text("'draft'"),
    ),
    sa.Column(
        "audience",
        sa.String(24),
        sa.CheckConstraint("audience IN ('adult','teen','child','all')"),
        nullable=False,
        server_default=sa.text("'adult'"),
    ),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.UniqueConstraint("question_id", "version"),
    schema="content",
)

daily_schedules_table = sa.Table(
    "daily_schedules",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("local_date", sa.Date(), nullable=False),
    sa.Column(
        "audience",
        sa.String(24),
        sa.CheckConstraint("audience IN ('adult','teen','child','all')"),
        nullable=False,
        server_default=sa.text("'adult'"),
    ),
    sa.Column(
        "question_version_id",
        sa.UUID(),
        sa.ForeignKey("content.question_versions.id"),
        nullable=False,
    ),
    sa.Column(
        "status",
        sa.String(16),
        sa.CheckConstraint("status IN ('scheduled','published','cancelled')"),
        nullable=False,
        server_default=sa.text("'scheduled'"),
    ),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.UniqueConstraint("local_date", "audience"),
    schema="content",
)
sa.Index(
    "ix_daily_schedules_date", daily_schedules_table.c.local_date, daily_schedules_table.c.audience
)
