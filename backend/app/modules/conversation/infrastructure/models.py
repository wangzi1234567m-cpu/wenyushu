"""Baseline persistence mapping; no business workflow is implemented here."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from app.infrastructure.db.base import Base

sessions_table = sa.Table(
    "sessions",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("actor_id", sa.UUID(), nullable=False),
    sa.Column(
        "kind",
        sa.String(24),
        sa.CheckConstraint("kind IN ('discussion')"),
        nullable=False,
        server_default=sa.text("'discussion'"),
    ),
    sa.Column("topic_id", sa.UUID()),
    sa.Column("policy_version", sa.String(64), nullable=False),
    sa.Column(
        "status",
        sa.String(16),
        sa.CheckConstraint("status IN ('active','closed','expired')"),
        nullable=False,
        server_default=sa.text("'active'"),
    ),
    sa.Column(
        "last_message_seq",
        sa.Integer(),
        sa.CheckConstraint("last_message_seq >= 0"),
        nullable=False,
        server_default=sa.text("0"),
    ),
    sa.Column("active_generation_id", sa.UUID()),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column(
        "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column("expires_at", sa.DateTime(timezone=True)),
    schema="conversation",
)
sa.Index("ix_sessions_actor", sessions_table.c.actor_id, sessions_table.c.created_at.desc())

messages_table = sa.Table(
    "messages",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column(
        "session_id",
        sa.UUID(),
        sa.ForeignKey("conversation.sessions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("seq", sa.Integer(), sa.CheckConstraint("seq >= 1"), nullable=False),
    sa.Column(
        "role", sa.String(12), sa.CheckConstraint("role IN ('user','assistant')"), nullable=False
    ),
    sa.Column(
        "status",
        sa.String(16),
        sa.CheckConstraint("status IN ('pending','generating','completed','failed','blocked')"),
        nullable=False,
    ),
    sa.Column("client_message_id", sa.String(128)),
    sa.Column("content", sa.Text(), nullable=False, server_default=sa.text("''")),
    sa.Column("model_name", sa.String(100)),
    sa.Column("tokens_in", sa.Integer(), sa.CheckConstraint("tokens_in IS NULL OR tokens_in >= 0")),
    sa.Column(
        "tokens_out", sa.Integer(), sa.CheckConstraint("tokens_out IS NULL OR tokens_out >= 0")
    ),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column("completed_at", sa.DateTime(timezone=True)),
    sa.UniqueConstraint("session_id", "seq"),
    sa.UniqueConstraint("session_id", "client_message_id"),
    schema="conversation",
)
sa.Index("ix_messages_session_seq", messages_table.c.session_id, messages_table.c.seq)

summaries_table = sa.Table(
    "summaries",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column(
        "session_id",
        sa.UUID(),
        sa.ForeignKey("conversation.sessions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("version", sa.Integer(), sa.CheckConstraint("version >= 1"), nullable=False),
    sa.Column(
        "covered_until_seq",
        sa.Integer(),
        sa.CheckConstraint("covered_until_seq >= 1"),
        nullable=False,
    ),
    sa.Column(
        "summary_json",
        JSONB(),
        sa.CheckConstraint("jsonb_typeof(summary_json) = 'object'"),
        nullable=False,
    ),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.UniqueConstraint("session_id", "version"),
    sa.UniqueConstraint("session_id", "covered_until_seq"),
    schema="conversation",
)
sa.Index(
    "ix_summaries_latest", summaries_table.c.session_id, summaries_table.c.covered_until_seq.desc()
)
