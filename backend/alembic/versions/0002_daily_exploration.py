"""Optional supplementary answer and idempotent daily reading intent."""

import sqlalchemy as sa
from alembic import op

revision = "0002_daily_exploration"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "exploration_answers", sa.Column("supplementary_text", sa.String(300)), schema="content"
    )
    op.create_index(
        "uq_daily_intent_source",
        "intents",
        ["actor_id", "source_type", "source_ref_id"],
        unique=True,
        schema="reading",
        postgresql_where=sa.text("source_type = 'daily_question' AND source_ref_id IS NOT NULL"),
    )


def downgrade():
    op.drop_index("uq_daily_intent_source", table_name="intents", schema="reading")
    op.drop_column("exploration_answers", "supplementary_text", schema="content")
