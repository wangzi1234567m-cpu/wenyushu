"""Never use a user database: tests require a DB name ending in _test."""

import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.infrastructure.db.metadata import metadata
from app.infrastructure.settings.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).parents[2]


def test_metadata_matches_migration(engine):
    with engine.connect() as conn:
        changes = compare_metadata(
            MigrationContext.configure(conn, opts={"include_schemas": True}), metadata
        )
        assert changes == []
        assert len(metadata.tables) == 19
        for table in metadata.sorted_tables:
            assert inspect(conn).has_table(table.name, schema=table.schema)


def test_frozen_migration_matches_reference_sql():
    import re

    from pglast import parse_sql

    path = ROOT / "backend/alembic/versions/0001_foundation.py"
    spec = importlib.util.spec_from_file_location("baseline", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    baseline = (ROOT / "db/schema.sql").read_text(encoding="utf-8")
    # Design reference now includes ADR-012; frozen 0001 must remain unchanged.
    baseline = re.sub(
        r"-- ADR-013:.*?CREATE TABLE discussion.contexts \(.*?\);", "", baseline, flags=re.S
    )
    baseline = baseline.replace("    option_ids jsonb,\n", "")
    baseline = re.sub(r"    CONSTRAINT ck_answer_option_ids[^\n]+\n", "", baseline)
    baseline = baseline.replace("    supplementary_text varchar(300),\n", "")
    baseline = re.sub(r"CREATE UNIQUE INDEX uq_daily_intent_source[^;]+;", "", baseline)
    baseline = re.sub(r"--[^\n]*", "", baseline)
    baseline = baseline.replace("BEGIN;", "").replace("COMMIT;", "")
    assert [x.stmt for x in parse_sql(baseline)] == [
        x.stmt for x in parse_sql(";".join(module.STATEMENTS))
    ]


def reject(conn, sql, params=None):
    with pytest.raises(IntegrityError), conn.begin_nested():
        conn.execute(text(sql), params or {})


def test_database_constraints(engine):
    actor = str(uuid4())
    with engine.connect() as conn, conn.begin():
        conn.execute(
            text(
                "INSERT INTO identity.actors(token_hash,expires_at) VALUES ('test',now()+interval '1 day')"
            )
        )
        reject(
            conn,
            "INSERT INTO identity.actors(token_hash,expires_at) VALUES ('test',now()+interval '1 day')",
        )
        reject(
            conn,
            "INSERT INTO identity.actors(token_hash,expires_at) VALUES ('expired',now()-interval '1 day')",
        )
        topic = conn.scalar(
            text("INSERT INTO content.topics(slug,title) VALUES ('x','x') RETURNING id")
        )
        question = conn.scalar(
            text("INSERT INTO content.questions(topic_id,slug) VALUES (:id,'x') RETURNING id"),
            {"id": topic},
        )
        version = conn.scalar(
            text(
                "INSERT INTO content.question_versions(question_id,version,title,intro,flow_json) VALUES (:id,1,'x','x','{}') RETURNING id"
            ),
            {"id": question},
        )
        reject(
            conn,
            "INSERT INTO content.question_versions(question_id,version,title,intro,flow_json) VALUES (:id,1,'x','x','{}')",
            {"id": question},
        )
        reject(
            conn,
            "INSERT INTO content.question_versions(question_id,version,title,intro,flow_json) VALUES (:id,2,'x','x','[]')",
            {"id": question},
        )
        for _ in range(1):
            conn.execute(
                text(
                    "INSERT INTO content.daily_schedules(local_date,question_version_id) VALUES ('2026-10-24',:id)"
                ),
                {"id": version},
            )
        reject(
            conn,
            "INSERT INTO content.daily_schedules(local_date,question_version_id) VALUES ('2026-10-24',:id)",
            {"id": version},
        )
        exploration = conn.scalar(
            text(
                "INSERT INTO content.explorations(actor_id,question_version_id,expires_at) VALUES (:actor,:v,now()+interval '1 day') RETURNING id"
            ),
            {"actor": actor, "v": version},
        )
        conn.execute(
            text(
                "INSERT INTO content.exploration_answers(exploration_id,step_id,option_id) VALUES (:id,'s','o')"
            ),
            {"id": exploration},
        )
        reject(
            conn,
            "INSERT INTO content.exploration_answers(exploration_id,step_id,option_id) VALUES (:id,'s','o2')",
            {"id": exploration},
        )
        session = conn.scalar(
            text(
                "INSERT INTO conversation.sessions(actor_id,policy_version) VALUES (:actor,'v1') RETURNING id"
            ),
            {"actor": actor},
        )
        conn.execute(
            text(
                "INSERT INTO conversation.messages(session_id,seq,role,status,client_message_id) VALUES (:id,1,'user','completed','c')"
            ),
            {"id": session},
        )
        reject(
            conn,
            "INSERT INTO conversation.messages(session_id,seq,role,status) VALUES (:id,1,'assistant','completed')",
            {"id": session},
        )
        reject(
            conn,
            "INSERT INTO conversation.messages(session_id,seq,role,status,client_message_id) VALUES (:id,2,'user','completed','c')",
            {"id": session},
        )
        reject(
            conn,
            "INSERT INTO conversation.messages(session_id,seq,role,status) VALUES (:id,0,'user','completed')",
            {"id": session},
        )
        reject(
            conn,
            "INSERT INTO conversation.messages(session_id,seq,role,status) VALUES (:id,2,'user','unknown')",
            {"id": session},
        )
        conn.execute(
            text(
                "INSERT INTO conversation.summaries(session_id,version,covered_until_seq,summary_json) VALUES (:id,1,1,'{}')"
            ),
            {"id": session},
        )
        reject(
            conn,
            "INSERT INTO conversation.summaries(session_id,version,covered_until_seq,summary_json) VALUES (:id,2,1,'{}')",
            {"id": session},
        )
        intent = conn.scalar(
            text(
                "INSERT INTO reading.intents(actor_id,source_type,purpose,preferences) VALUES (:actor,'direct_search','interest','{}') RETURNING id"
            ),
            {"actor": actor},
        )
        job_params = {"actor": actor, "id": intent}
        job_sql = "INSERT INTO reading.recommendation_jobs(actor_id,reading_intent_id,idempotency_key,request_hash) VALUES (:actor,:id,'key',repeat('a',64))"
        job = conn.scalar(text(job_sql + " RETURNING id"), job_params)
        reject(conn, job_sql, job_params)
        reject(
            conn,
            "UPDATE reading.recommendation_jobs SET requested_limit=4 WHERE id=:id",
            {"id": job},
        )
        reject(
            conn, "UPDATE reading.recommendation_jobs SET max_attempts=11 WHERE id=:id", {"id": job}
        )
        work = conn.scalar(
            text(
                "INSERT INTO catalog.works(canonical_title,author) VALUES ('fixture','fixture') RETURNING id"
            )
        )
        item_sql = "INSERT INTO reading.recommendation_items(job_id,work_id,rank,title,author,summary,recommendation_reason,verification_status,evidence_urls) VALUES (:job,:work,1,'x','x','x','x','verified',:evidence)"
        reject(conn, item_sql, {"job": job, "work": work, "evidence": "[]"})
        conn.execute(
            text(item_sql),
            {"job": job, "work": work, "evidence": '["https://example.invalid/test"]'},
        )
        reject(
            conn,
            item_sql,
            {"job": job, "work": work, "evidence": '["https://example.invalid/test"]'},
        )
        conn.execute(
            text("INSERT INTO catalog.editions(work_id,isbn13) VALUES (:id,'1234567890123')"),
            {"id": work},
        )
        reject(
            conn,
            "INSERT INTO catalog.editions(work_id,isbn13) VALUES (:id,'1234567890123')",
            {"id": work},
        )
        reject(
            conn, "INSERT INTO catalog.editions(work_id,isbn13) VALUES (:id,'bad')", {"id": work}
        )
        reject(conn, "INSERT INTO catalog.editions(work_id) VALUES (:id)", {"id": uuid4()})
        handoff = "INSERT INTO handoff.jobs(actor_id,conversation_id,up_to_seq,idempotency_key,request_hash) VALUES (:actor,:id,1,'k',repeat('b',64))"
        conn.execute(text(handoff), {"actor": actor, "id": session})
        reject(conn, handoff, {"actor": actor, "id": session})
        reject(
            conn,
            "INSERT INTO safety.reports(actor_id,target_type,target_id,reason) VALUES (:actor,'message',:id,'invalid')",
            {"actor": actor, "id": session},
        )
        conn.execute(text("DELETE FROM conversation.sessions WHERE id=:id"), {"id": session})
        assert (
            conn.scalar(
                text("SELECT count(*) FROM conversation.messages WHERE session_id=:id"),
                {"id": session},
            )
            == 0
        )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM conversation.summaries WHERE session_id=:id"),
                {"id": session},
            )
            == 0
        )


def test_real_identity_roundtrip(engine):
    settings = Settings(
        _env_file=None,
        provider="mock",
        database_url=os.environ["TEST_DATABASE_URL"],
        csrf_secret="isolated-test-secret-not-for-production",
        environment="test",
        allowed_origins=["https://testserver"],
    )
    with TestClient(
        create_app(settings),
        base_url="https://testserver",
        headers={"Origin": "https://testserver"},
    ) as client:
        assert client.get("/api/v1/health/ready").status_code == 200
        response = client.post("/api/v1/auth/anonymous-session")
        token = client.cookies.get("wqs_session")
        assert response.status_code == 201
        assert client.post("/api/v1/auth/anonymous-session").status_code == 201
        assert client.cookies.get("wqs_session") == token
        assert (
            client.delete(
                "/api/v1/auth/anonymous-session",
                headers={"X-CSRF-Token": response.json()["csrf_token"]},
            ).status_code
            == 200
        )
