"""Baseline persistence mapping; no business workflow is implemented here."""

import sqlalchemy as sa

from app.infrastructure.db.base import Base

reports_table = sa.Table(
    "reports",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("actor_id", sa.UUID(), nullable=False),
    sa.Column(
        "target_type",
        sa.String(24),
        sa.CheckConstraint("target_type IN ('message','recommendation')"),
        nullable=False,
    ),
    sa.Column("target_id", sa.UUID(), nullable=False),
    sa.Column(
        "reason",
        sa.String(40),
        sa.CheckConstraint("reason IN ('harmful','inaccurate','copyright','privacy','other')"),
        nullable=False,
    ),
    sa.Column("detail", sa.Text()),
    sa.Column(
        "status",
        sa.String(16),
        sa.CheckConstraint("status IN ('open','reviewing','resolved','dismissed')"),
        nullable=False,
        server_default=sa.text("'open'"),
    ),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    schema="safety",
)
sa.Index("ix_reports_status", reports_table.c.status, reports_table.c.created_at.desc())
