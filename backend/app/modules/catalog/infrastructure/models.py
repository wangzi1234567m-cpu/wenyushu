"""Baseline persistence mapping; no business workflow is implemented here."""

import sqlalchemy as sa

from app.infrastructure.db.base import Base

works_table = sa.Table(
    "works",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("canonical_title", sa.String(400), nullable=False),
    sa.Column("author", sa.String(300), nullable=False),
    sa.Column("original_title", sa.String(400)),
    sa.Column("language", sa.String(24)),
    sa.Column("normalized_key", sa.String(800), unique=True),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column(
        "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    schema="catalog",
)
sa.Index("ix_works_title_author", works_table.c.canonical_title, works_table.c.author)

editions_table = sa.Table(
    "editions",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column(
        "work_id", sa.UUID(), sa.ForeignKey("catalog.works.id", ondelete="CASCADE"), nullable=False
    ),
    sa.Column("isbn13", sa.CHAR(13), unique=True),
    sa.Column("publisher", sa.String(300)),
    sa.Column("translator", sa.String(300)),
    sa.Column(
        "publication_year",
        sa.Integer(),
        sa.CheckConstraint("publication_year IS NULL OR publication_year BETWEEN 1000 AND 2200"),
    ),
    sa.Column("cover_url", sa.Text()),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.CheckConstraint("isbn13 IS NULL OR isbn13 ~ '^[0-9]{13}$'"),
    schema="catalog",
)

evidence_table = sa.Table(
    "evidence",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column(
        "work_id", sa.UUID(), sa.ForeignKey("catalog.works.id", ondelete="CASCADE"), nullable=False
    ),
    sa.Column(
        "source_type",
        sa.String(32),
        sa.CheckConstraint("source_type IN ('publisher','library','catalog','review','other')"),
        nullable=False,
    ),
    sa.Column("source_url", sa.Text(), nullable=False),
    sa.Column(
        "claim_type",
        sa.String(24),
        sa.CheckConstraint(
            "claim_type IN ('bibliography','synopsis','theme','edition','quotation')"
        ),
        nullable=False,
    ),
    sa.Column("evidence_summary", sa.Text(), nullable=False),
    sa.Column(
        "verification_status",
        sa.String(16),
        sa.CheckConstraint("verification_status IN ('pending','verified','rejected','stale')"),
        nullable=False,
        server_default=sa.text("'pending'"),
    ),
    sa.Column("checked_at", sa.DateTime(timezone=True)),
    sa.Column("expires_at", sa.DateTime(timezone=True)),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    schema="catalog",
)
sa.Index(
    "ix_evidence_work_status",
    evidence_table.c.work_id,
    evidence_table.c.verification_status,
    evidence_table.c.claim_type,
)
