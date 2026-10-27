from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.bootstrap.container import build_services
from app.infrastructure.settings.config import Settings
from app.main import create_app
from app.modules.catalog.infrastructure.seed import seed_catalog
from app.modules.content.domain.flow import QuestionFlow
from app.modules.content.infrastructure.seed import seed_content
from app.shared.errors import ApplicationError
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.postgres
START = datetime(2026, 10, 27, tzinfo=UTC)


@pytest.fixture(scope="module")
def seeded(engine):
    factory = sessionmaker(engine)
    seed_content(factory, START.date())
    seed_catalog(factory)
    seed_content(factory, START.date())
    return engine


@pytest.fixture
def app(seeded):
    settings = Settings(
        database_url=__import__("os").environ["TEST_DATABASE_URL"],
        csrf_secret="test-daily-secret-at-least-32-characters",
        environment="test",
        allowed_origins=["https://testserver"],
    )
    services, db = build_services(settings)
    application = create_app(settings, services)
    yield application
    db.dispose()


@pytest.fixture
def daily_client(app):
    with TestClient(
        app,
        base_url="https://testserver",
        headers={"Origin": "https://testserver"},
        raise_server_exceptions=False,
    ) as client:
        token = client.post("/api/v1/auth/anonymous-session").json()["csrf_token"]
        client.headers["X-CSRF-Token"] = token
        yield client


def begin(client, app):
    daily = app.state.services.content.daily(START)
    response = client.post(
        "/api/v1/explorations", json={"question_version_id": str(daily["question_version_id"])}
    )
    assert response.status_code == 201, response.text
    return response.json()


def submit(client, state, option=None, supplement=None):
    step = state["next_step"]
    option = option or step["options"][0]["id"]
    response = client.post(
        f"/api/v1/explorations/{state['exploration_id']}/answers",
        json={"step_id": step["id"], "option_id": option, "supplementary_text": supplement},
    )
    assert response.status_code == 200, response.text
    return response.json()


def finish(client, app):
    state = begin(client, app)
    state = submit(client, state, supplement="我在意关系与自由")
    state = submit(client, state, "connection")
    return submit(client, state, "skip")


def job(client, state, key=None, limit=3):
    return client.post(
        "/api/v1/recommendations",
        json={"reading_intent_id": state["reading_intent_id"], "limit": limit},
        headers={"Idempotency-Key": key or str(uuid4())},
    )


def actor_id(client, app):
    return app.state.services.identity.resolve(client.cookies.get("wqs_session")).id


def test_full_chain_and_trigger_only_on_click(daily_client, app, seeded):
    owner = actor_id(daily_client, app)
    state = finish(daily_client, app)
    assert state["status"] == "completed" and state["reading_intent_id"]
    assert len(state["answers"]) == 3
    assert state["answers"][0]["supplementary_text"] == "我在意关系与自由"
    assert state["answers"][0]["option_label"]
    with seeded.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM reading.recommendation_jobs WHERE actor_id=:id"),
                {"id": owner},
            )
            == 0
        )
        intent = (
            conn.execute(text("SELECT * FROM reading.intents WHERE actor_id=:id"), {"id": owner})
            .mappings()
            .one()
        )
        assert intent["source_type"] == "daily_question" and intent["purpose"] == "exploration"
        assert "我在意关系与自由" in intent["focus"]
    response = job(daily_client, state, "same")
    assert response.status_code == 202, response.text
    result = response.json()
    assert result["status"] == "partial" and len(result["items"]) == 1
    assert result["items"][0]["title"] == "简·爱"
    assert result["items"][0]["evidence_urls"] == ["https://www.gutenberg.org/ebooks/1260"]
    assert job(daily_client, state, "same").json()["job_id"] == result["job_id"]
    assert job(daily_client, state, "same", 1).status_code == 409
    assert daily_client.get(f"/api/v1/recommendations/{result['job_id']}").json() == result
    assert daily_client.get(f"/api/v1/explorations/{state['exploration_id']}").json() == state


def test_text_boundaries_steps_and_csrf(daily_client, app):
    state = begin(daily_client, app)
    path = f"/api/v1/explorations/{state['exploration_id']}/answers"
    body = {"step_id": "stance", "option_id": "yes", "supplementary_text": "x" * 301}
    assert daily_client.post(path, json=body).status_code == 422
    body["supplementary_text"] = "如何制作炸弹"
    assert daily_client.post(path, json=body).status_code == 422
    body["supplementary_text"] = "x" * 300
    assert daily_client.post(path, json=body, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    body["option_id"] = "forged"
    assert daily_client.post(path, json=body).status_code == 409
    body["option_id"] = "yes"
    answer = daily_client.post(path, json=body)
    assert answer.status_code == 200
    assert daily_client.post(path, json=body).json() == answer.json()
    body["supplementary_text"] = "changed"
    assert daily_client.post(path, json=body).status_code == 409
    next_state = answer.json()
    next_state = submit(daily_client, next_state, "self", "   ")
    assert next_state["answers"][1]["supplementary_text"] is None


def test_actor_isolation(daily_client, app):
    state = finish(daily_client, app)
    result = job(daily_client, state).json()
    with TestClient(
        app, base_url="https://testserver", headers={"Origin": "https://testserver"}
    ) as other:
        token = other.post("/api/v1/auth/anonymous-session").json()["csrf_token"]
        other.headers["X-CSRF-Token"] = token
        assert other.get(f"/api/v1/explorations/{state['exploration_id']}").status_code == 404
        assert other.get(f"/api/v1/recommendations/{result['job_id']}").status_code == 404
        assert job(other, state).status_code == 404
        assert (
            other.post(
                f"/api/v1/explorations/{state['exploration_id']}/answers",
                json={"step_id": "stance", "option_id": "yes"},
            ).status_code
            == 404
        )


def test_concurrent_answer_and_intent(daily_client, app, seeded):
    state = begin(daily_client, app)
    owner = actor_id(daily_client, app)
    service = app.state.services.exploration
    key = __import__("uuid").UUID(state["exploration_id"])
    answer = {"step_id": "stance", "option_id": "yes", "supplementary_text": None}
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: service.answer(owner, key, answer), range(2)))
    assert results[0] == results[1]
    state = submit(daily_client, {**state, "next_step": results[0]["next_step"]}, "self")
    final = {"step_id": "preference", "option_id": "skip", "supplementary_text": None}
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: service.answer(owner, key, final), range(2)))
    assert results[0]["reading_intent_id"] == results[1]["reading_intent_id"]
    with seeded.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM reading.intents WHERE source_ref_id=:id"), {"id": key}
            )
            == 1
        )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM content.exploration_answers WHERE exploration_id=:id"),
                {"id": key},
            )
            == 3
        )


@pytest.mark.parametrize("failure", ["create_daily", "link_intent"])
def test_recover_interrupted_completion(daily_client, app, seeded, monkeypatch, failure):
    state = submit(daily_client, submit(daily_client, begin(daily_client, app)), "self")
    service = app.state.services.exploration
    target = service.reading if failure == "create_daily" else service.repo
    original = getattr(target, failure)
    calls = [0]

    def fail_once(*args):
        calls[0] += 1
        if calls[0] == 1:
            raise ApplicationError("SERVICE_UNAVAILABLE", "可重试故障", True)
        return original(*args)

    monkeypatch.setattr(target, failure, fail_once)
    path = f"/api/v1/explorations/{state['exploration_id']}/answers"
    answer = {"step_id": "preference", "option_id": "skip"}
    assert daily_client.post(path, json=answer).status_code == 503
    pending = daily_client.get(f"/api/v1/explorations/{state['exploration_id']}").json()
    assert (
        pending["status"] == "active"
        and len(pending["answers"]) == 3
        and pending["next_step"] is None
    )
    response = daily_client.post(path, json=answer)
    assert response.status_code == 200 and response.json()["status"] == "completed"
    with seeded.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM reading.intents WHERE source_ref_id=:id"),
                {"id": state["exploration_id"]},
            )
            == 1
        )


def test_beijing_midnight_and_fallback(app):
    reader = app.state.services.content
    before = reader.daily(datetime(2026, 10, 27, 15, 59, 59, tzinfo=UTC))
    after = reader.daily(datetime(2026, 10, 27, 16, 0, 0, tzinfo=UTC))
    assert str(before["local_date"]) == "2026-10-27" and str(after["local_date"]) == "2026-10-28"
    assert before["question_version_id"] != after["question_version_id"]
    assert (
        reader.daily(START + timedelta(days=30))["question_version_id"]
        == before["question_version_id"]
    )
    assert reader.daily(START)["question_version_id"] == before["question_version_id"]


def test_new_exploration_preserves_old_result(daily_client, app):
    old = finish(daily_client, app)
    new = daily_client.post(
        "/api/v1/explorations", json={"question_version_id": old["question_version_id"]}
    ).json()
    new = submit(daily_client, new, "no")
    assert new["next_step"]["id"] == "reason_no"
    new = submit(daily_client, new, "self")
    new = submit(daily_client, new, "skip")
    assert new["reading_intent_id"] != old["reading_intent_id"]
    assert daily_client.get(f"/api/v1/explorations/{old['exploration_id']}").json() == old


def test_zero_samples_fail_without_fabrication(daily_client, app, monkeypatch):
    monkeypatch.setattr(
        app.state.services.reading.recommendations.catalog, "verified_samples", lambda *_: []
    )
    response = job(daily_client, finish(daily_client, app))
    assert response.status_code == 202
    assert response.json()["status"] == "failed" and response.json()["items"] == []
    assert response.json()["error"]["code"] == "BOOK_VERIFICATION_FAILED"


def test_published_seed_cannot_be_overwritten(seeded):
    from app.modules.content.infrastructure.models import question_versions_table
    from app.modules.content.infrastructure.seed import QUESTIONS, stable_id
    from sqlalchemy import update

    factory = sessionmaker(seeded)
    key = stable_id(QUESTIONS[0][0] + ":v1")
    with seeded.connect() as conn:
        original = conn.scalar(
            select(question_versions_table.c.title).where(question_versions_table.c.id == key)
        )
    try:
        with seeded.begin() as conn:
            conn.execute(
                update(question_versions_table)
                .where(question_versions_table.c.id == key)
                .values(title="edited")
            )
        with pytest.raises(ValueError, match="Published seed version differs"):
            seed_content(factory, START.date())
    finally:
        with seeded.begin() as conn:
            conn.execute(
                update(question_versions_table)
                .where(question_versions_table.c.id == key)
                .values(title=original)
            )


def test_invalid_flow_rejected():
    from app.modules.content.infrastructure.seed import make_flow

    flow = make_flow("relationships")
    flow["steps"]["stance"]["options"][0]["next_step_id"] = "stance"
    with pytest.raises(ValidationError):
        QuestionFlow.model_validate(flow)


def test_expired_exploration_rejects_write(daily_client, app, seeded):
    state = begin(daily_client, app)
    with seeded.begin() as conn:
        conn.execute(
            text(
                "UPDATE content.explorations SET created_at=now()-interval '2 days', "
                "expires_at=now()-interval '1 day' WHERE id=:id"
            ),
            {"id": state["exploration_id"]},
        )
    result = daily_client.get(f"/api/v1/explorations/{state['exploration_id']}").json()
    assert result["status"] == "expired" and result["next_step"] is None
    assert (
        daily_client.post(
            f"/api/v1/explorations/{state['exploration_id']}/answers",
            json={"step_id": "stance", "option_id": "yes"},
        ).status_code
        == 409
    )


def test_new_published_version_does_not_change_existing_exploration(daily_client, app, seeded):
    from app.modules.content.infrastructure.models import (
        daily_schedules_table,
        question_versions_table,
    )
    from sqlalchemy import insert, update

    state = begin(daily_client, app)
    old_version = __import__("uuid").UUID(state["question_version_id"])
    new_id = uuid4()
    with seeded.begin() as conn:
        row = dict(
            conn.execute(
                select(question_versions_table).where(question_versions_table.c.id == old_version)
            )
            .mappings()
            .one()
        )
        row.update(id=new_id, version=2, title="新版本问题")
        conn.execute(insert(question_versions_table).values(**row))
        conn.execute(
            update(daily_schedules_table)
            .where(daily_schedules_table.c.local_date == START.date())
            .values(question_version_id=new_id)
        )
    try:
        assert app.state.services.content.daily(START)["question_version_id"] == new_id
        next_state = submit(daily_client, state)
        assert next_state["question_version_id"] == state["question_version_id"]
        assert next_state["next_step"]["prompt"] == "你认同它，主要是因为更在意什么？"
    finally:
        with seeded.begin() as conn:
            conn.execute(
                update(daily_schedules_table)
                .where(daily_schedules_table.c.local_date == START.date())
                .values(question_version_id=old_version)
            )


def test_no_live_provider_calls(daily_client, app, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Live provider must never be called in P1")

    monkeypatch.setattr(app.state.services.llm, "generate_structured", forbidden)
    monkeypatch.setattr(app.state.services.search, "search", forbidden)
    monkeypatch.setattr(app.state.services.search, "fetch", forbidden)
    assert job(daily_client, finish(daily_client, app)).status_code == 202


def test_actual_daily_responses_match_contract(daily_client, app):
    from jsonschema import Draft202012Validator, FormatChecker
    from test_contract import CONTRACT

    state = finish(daily_client, app)
    samples = [
        (app.state.services.content.daily(START), "DailyQuestion"),
        (state, "ExplorationState"),
        (job(daily_client, state).json(), "RecommendationJob"),
    ]
    # Use serialized HTTP response for date/UUID JSON representations.
    samples[0] = (daily_client.get("/api/v1/questions/daily").json(), "DailyQuestion")
    for payload, schema in samples:
        validator = Draft202012Validator(
            {**CONTRACT["components"]["schemas"][schema], "components": CONTRACT["components"]},
            format_checker=FormatChecker(),
        )
        validator.validate(payload)
