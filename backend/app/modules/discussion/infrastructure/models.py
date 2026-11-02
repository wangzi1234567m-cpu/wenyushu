import sqlalchemy as sa
from app.infrastructure.db.base import Base
from sqlalchemy.dialects.postgresql import JSONB

contexts_table = sa.Table(
    "contexts",
    Base.metadata,
    sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("actor_id", sa.UUID(), nullable=False),
    sa.Column("conversation_id", sa.UUID(), nullable=False, unique=True),
    sa.Column("exploration_id", sa.UUID()),
    sa.Column("context_json", JSONB(), nullable=False),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.CheckConstraint("jsonb_typeof(context_json) = 'object'"),
    sa.UniqueConstraint("actor_id", "exploration_id"),
    schema="discussion",
)

extractions_table = sa.Table(
    "viewpoint_extractions",
    Base.metadata,
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

saved_viewpoints_table = sa.Table(
    "saved_viewpoints",
    Base.metadata,
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
        "jsonb_typeof(source_message_ids) = 'array' "
        "AND jsonb_array_length(source_message_ids) BETWEEN 1 AND 4"
    ),
    schema="discussion",
)
sa.Index(
    "ix_saved_viewpoints_actor",
    saved_viewpoints_table.c.actor_id,
    saved_viewpoints_table.c.created_at,
    saved_viewpoints_table.c.id,
)
