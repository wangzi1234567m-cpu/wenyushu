"""Baseline persistence mapping; no business workflow is implemented here."""

import sqlalchemy as sa

from app.infrastructure.db.base import Base

actors_table = sa.Table(
    "actors",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("revoked_at", sa.DateTime(timezone=True)),
    sa.CheckConstraint("expires_at > created_at"),
    schema="identity",
)
sa.Index("ix_identity_actors_expires", actors_table.c.expires_at)


class ActorRow(Base):
    __table__ = actors_table
