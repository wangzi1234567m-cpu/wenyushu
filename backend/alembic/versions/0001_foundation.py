"""Frozen SAD V1.0 baseline. Alembic is the only migration entrypoint."""

from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None

STATEMENTS = [
    """CREATE SCHEMA IF NOT EXISTS identity""",
    """CREATE SCHEMA IF NOT EXISTS content""",
    """CREATE SCHEMA IF NOT EXISTS conversation""",
    """CREATE SCHEMA IF NOT EXISTS reading""",
    """CREATE SCHEMA IF NOT EXISTS catalog""",
    """CREATE SCHEMA IF NOT EXISTS handoff""",
    """CREATE SCHEMA IF NOT EXISTS safety""",
    """CREATE TABLE identity.actors (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CHECK (expires_at > created_at)
)""",
    """CREATE INDEX ix_identity_actors_expires ON identity.actors(expires_at)""",
    """CREATE TABLE content.topics (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug varchar(96) NOT NULL UNIQUE,
    title varchar(200) NOT NULL,
    description text,
    audience varchar(24) NOT NULL DEFAULT 'adult' CHECK (audience IN ('adult','teen','child','all')),
    status varchar(16) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published','archived')),
    created_at timestamptz NOT NULL DEFAULT now()
)""",
    """CREATE TABLE content.questions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id uuid NOT NULL REFERENCES content.topics(id),
    slug varchar(96) NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
)""",
    """CREATE TABLE content.question_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id uuid NOT NULL REFERENCES content.questions(id),
    version integer NOT NULL CHECK (version >= 1),
    title varchar(300) NOT NULL,
    intro text NOT NULL,
    flow_json jsonb NOT NULL CHECK (jsonb_typeof(flow_json) = 'object'),
    status varchar(16) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','reviewed','published','archived')),
    audience varchar(24) NOT NULL DEFAULT 'adult' CHECK (audience IN ('adult','teen','child','all')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (question_id,version)
)""",
    """CREATE TABLE content.daily_schedules (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    local_date date NOT NULL,
    audience varchar(24) NOT NULL DEFAULT 'adult' CHECK (audience IN ('adult','teen','child','all')),
    question_version_id uuid NOT NULL REFERENCES content.question_versions(id),
    status varchar(16) NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled','published','cancelled')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(local_date,audience)
)""",
    """CREATE INDEX ix_daily_schedules_date ON content.daily_schedules(local_date,audience)""",
    """CREATE TABLE content.explorations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id uuid NOT NULL, 
    question_version_id uuid NOT NULL REFERENCES content.question_versions(id),
    status varchar(16) NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','expired')),
    current_step_id varchar(96),
    reading_intent_id uuid, 
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    CHECK (expires_at > created_at)
)""",
    """CREATE INDEX ix_explorations_actor ON content.explorations(actor_id,created_at DESC)""",
    """CREATE TABLE content.exploration_answers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exploration_id uuid NOT NULL REFERENCES content.explorations(id) ON DELETE CASCADE,
    step_id varchar(96) NOT NULL,
    option_id varchar(96) NOT NULL,
    submitted_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(exploration_id,step_id)
)""",
    """CREATE TABLE conversation.sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id uuid NOT NULL,
    kind varchar(24) NOT NULL DEFAULT 'discussion' CHECK (kind IN ('discussion')), 
    topic_id uuid, 
    policy_version varchar(64) NOT NULL,
    status varchar(16) NOT NULL DEFAULT 'active' CHECK (status IN ('active','closed','expired')),
    last_message_seq integer NOT NULL DEFAULT 0 CHECK (last_message_seq >= 0),
    active_generation_id uuid, 
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz
)""",
    """CREATE INDEX ix_sessions_actor ON conversation.sessions(actor_id,created_at DESC)""",
    """CREATE TABLE conversation.messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES conversation.sessions(id) ON DELETE CASCADE,
    seq integer NOT NULL CHECK (seq >= 1),
    role varchar(12) NOT NULL CHECK (role IN ('user','assistant')),
    status varchar(16) NOT NULL CHECK (status IN ('pending','generating','completed','failed','blocked')),
    client_message_id varchar(128),
    content text NOT NULL DEFAULT '',
    model_name varchar(100),
    tokens_in integer CHECK (tokens_in IS NULL OR tokens_in >= 0),
    tokens_out integer CHECK (tokens_out IS NULL OR tokens_out >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    UNIQUE(session_id,seq),
    UNIQUE(session_id,client_message_id)
)""",
    """CREATE INDEX ix_messages_session_seq ON conversation.messages(session_id,seq)""",
    """CREATE TABLE conversation.summaries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES conversation.sessions(id) ON DELETE CASCADE,
    version integer NOT NULL CHECK (version >= 1),
    covered_until_seq integer NOT NULL CHECK (covered_until_seq >= 1),
    summary_json jsonb NOT NULL CHECK (jsonb_typeof(summary_json) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(session_id,version),
    UNIQUE(session_id,covered_until_seq)
)""",
    """CREATE INDEX ix_summaries_latest ON conversation.summaries(session_id,covered_until_seq DESC)""",
    """CREATE TABLE reading.intents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id uuid NOT NULL,
    source_type varchar(24) NOT NULL CHECK (source_type IN ('daily_question','direct_search','discussion')),
    source_ref_id uuid,
    purpose varchar(24) NOT NULL CHECK (purpose IN ('interest','learning','exploration')),
    central_question text,
    topics jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(topics) = 'array'),
    focus text,
    preferences jsonb NOT NULL CHECK (jsonb_typeof(preferences) = 'object'),
    schema_version integer NOT NULL DEFAULT 1 CHECK (schema_version >= 1),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz
)""",
    """CREATE INDEX ix_intents_actor ON reading.intents(actor_id,created_at DESC)""",
    """CREATE TABLE reading.recommendation_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id uuid NOT NULL,
    reading_intent_id uuid NOT NULL REFERENCES reading.intents(id),
    idempotency_key varchar(128) NOT NULL,
    request_hash char(64) NOT NULL,
    requested_limit integer NOT NULL DEFAULT 3 CHECK (requested_limit BETWEEN 1 AND 3),
    status varchar(16) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','succeeded','partial','failed')),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 10),
    lease_until timestamptz,
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    error_code varchar(80),
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    UNIQUE(actor_id,idempotency_key)
)""",
    """CREATE INDEX ix_recommendation_jobs_queue ON reading.recommendation_jobs(status,next_attempt_at,lease_until)""",
    """CREATE TABLE reading.recommendation_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id uuid NOT NULL REFERENCES reading.recommendation_jobs(id) ON DELETE CASCADE,
    work_id uuid NOT NULL, 
    rank integer NOT NULL CHECK(rank BETWEEN 1 AND 3),
    title varchar(400) NOT NULL,
    author varchar(300) NOT NULL,
    summary text NOT NULL,
    recommendation_reason text NOT NULL,
    verification_status varchar(20) NOT NULL CHECK(verification_status IN ('verified')),
    evidence_urls jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(evidence_urls) = 'array' AND jsonb_array_length(evidence_urls) >= 1),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(job_id,rank),
    UNIQUE(job_id,work_id)
)""",
    """CREATE TABLE catalog.works (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_title varchar(400) NOT NULL,
    author varchar(300) NOT NULL,
    original_title varchar(400),
    language varchar(24),
    normalized_key varchar(800) UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
)""",
    """CREATE INDEX ix_works_title_author ON catalog.works(canonical_title,author)""",
    """CREATE TABLE catalog.editions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    work_id uuid NOT NULL REFERENCES catalog.works(id) ON DELETE CASCADE,
    isbn13 char(13) UNIQUE,
    publisher varchar(300),
    translator varchar(300),
    publication_year integer CHECK(publication_year IS NULL OR publication_year BETWEEN 1000 AND 2200),
    cover_url text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (isbn13 IS NULL OR isbn13 ~ '^[0-9]{13}$')
)""",
    """CREATE TABLE catalog.evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    work_id uuid NOT NULL REFERENCES catalog.works(id) ON DELETE CASCADE,
    source_type varchar(32) NOT NULL CHECK (source_type IN ('publisher','library','catalog','review','other')),
    source_url text NOT NULL,
    claim_type varchar(24) NOT NULL CHECK (claim_type IN ('bibliography','synopsis','theme','edition','quotation')),
    evidence_summary text NOT NULL,
    verification_status varchar(16) NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending','verified','rejected','stale')),
    checked_at timestamptz,
    expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
)""",
    """CREATE INDEX ix_evidence_work_status ON catalog.evidence(work_id,verification_status,claim_type)""",
    """CREATE TABLE handoff.jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id uuid NOT NULL,
    conversation_id uuid NOT NULL, 
    up_to_seq integer NOT NULL CHECK(up_to_seq >= 0),
    idempotency_key varchar(128) NOT NULL,
    request_hash char(64) NOT NULL,
    status varchar(16) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','succeeded','partial','failed')),
    reading_intent_id uuid,
    recommendation_job_id uuid,
    topic_summary text,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 10),
    lease_until timestamptz,
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    error_code varchar(80),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    UNIQUE(actor_id,idempotency_key)
)""",
    """CREATE INDEX ix_handoff_queue ON handoff.jobs(status,next_attempt_at,lease_until)""",
    """CREATE TABLE safety.reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id uuid NOT NULL,
    target_type varchar(24) NOT NULL CHECK (target_type IN ('message','recommendation')),
    target_id uuid NOT NULL,
    reason varchar(40) NOT NULL CHECK (reason IN ('harmful','inaccurate','copyright','privacy','other')),
    detail text,
    status varchar(16) NOT NULL DEFAULT 'open' CHECK (status IN ('open','reviewing','resolved','dismissed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    reviewed_at timestamptz
)""",
    """CREATE INDEX ix_reports_status ON safety.reports(status,created_at DESC)""",
]


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    op.execute("DROP TABLE safety.reports")
    op.execute("DROP TABLE handoff.jobs")
    op.execute("DROP TABLE catalog.evidence")
    op.execute("DROP TABLE catalog.editions")
    op.execute("DROP TABLE catalog.works")
    op.execute("DROP TABLE reading.recommendation_items")
    op.execute("DROP TABLE reading.recommendation_jobs")
    op.execute("DROP TABLE reading.intents")
    op.execute("DROP TABLE conversation.summaries")
    op.execute("DROP TABLE conversation.messages")
    op.execute("DROP TABLE conversation.sessions")
    op.execute("DROP TABLE content.exploration_answers")
    op.execute("DROP TABLE content.explorations")
    op.execute("DROP TABLE content.daily_schedules")
    op.execute("DROP TABLE content.question_versions")
    op.execute("DROP TABLE content.questions")
    op.execute("DROP TABLE content.topics")
    op.execute("DROP TABLE identity.actors")
    op.execute("DROP SCHEMA safety")
    op.execute("DROP SCHEMA handoff")
    op.execute("DROP SCHEMA catalog")
    op.execute("DROP SCHEMA reading")
    op.execute("DROP SCHEMA conversation")
    op.execute("DROP SCHEMA content")
    op.execute("DROP SCHEMA identity")
