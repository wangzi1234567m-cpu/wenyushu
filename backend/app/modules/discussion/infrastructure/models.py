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
