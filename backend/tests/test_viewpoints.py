import os
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from app.bootstrap.container import build_services
from app.infrastructure.settings.config import Settings
from app.integrations.llm.mock import MockLLM
from app.main import create_app
from app.shared.errors import ApplicationError
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def app(engine):
    settings = Settings(
        _env_file=None,
        provider="mock",
        environment="test",
        database_url=os.environ["TEST_DATABASE_URL"],
        csrf_secret="test-viewpoints-secret-with-at-least-32-characters",
        allowed_origins=["https://testserver"],
    )
    services, db = build_services(settings)
    yield create_app(settings, services)
    db.dispose()


@pytest.fixture
def client(app):
    with TestClient(
        app, base_url="https://testserver", headers={"Origin": "https://testserver"}
    ) as c:
        c.headers["X-CSRF-Token"] = c.post("/api/v1/auth/anonymous-session").json()["csrf_token"]
        yield c


def discussion(c):
    key = c.post("/api/v1/conversations", json={"kind": "discussion", "topic_id": None}).json()[
        "conversation_id"
    ]
    r = c.post(
        f"/api/v1/conversations/{key}/messages",
        json={"client_message_id": "test", "content": "我想要自由，但又不想承担自由带来的风险。"},
    )
    assert "message_completed" in r.text
    rows = c.get(f"/api/v1/conversations/{key}/messages").json()["messages"]
    return key, rows


def extract(c, key):
    return c.post(f"/api/v1/conversations/{key}/viewpoints", json={"up_to_seq": 2})


def test_exact_quotes_idempotency_refresh_paging_cancel(client, engine):
    key, rows = discussion(client)
    for row, kind in zip(rows, ["user_quote", "ai_viewpoint"]):
        source = {"conversation_id": key, "message_id": row["id"]}
        saved = client.post("/api/v1/saved-viewpoints", json=source)
        assert saved.status_code == 201, saved.text
        point = saved.json()
        assert point["content"] == row["content"] and point["source_type"] == kind
        assert client.post("/api/v1/saved-viewpoints", json=source).json() == point
    page = client.get("/api/v1/saved-viewpoints?limit=1").json()
    assert len(page["items"]) == 1 and page["next_offset"] == 1
    second = client.get("/api/v1/saved-viewpoints?limit=1&offset=1").json()
    assert second["next_offset"] is None and second["items"][0]["id"] != page["items"][0]["id"]
    assert client.delete(f"/api/v1/saved-viewpoints/{point['id']}").status_code == 200
    assert len(client.get("/api/v1/saved-viewpoints").json()["items"]) == 1
    assert client.post("/api/v1/saved-viewpoints", json=source).json()["id"] == point["id"]
    with engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM discussion.saved_viewpoints WHERE conversation_id=:id"),
                {"id": key},
            )
            == 2
        )


def test_extraction_grounded_cached_no_auto_save(client, app, monkeypatch):
    key, rows = discussion(client)
    llm = app.state.services.viewpoints.llm
    original = llm.generate_structured
    calls = []

    async def counted(*args):
        calls.append(args)
        return await original(*args)

    monkeypatch.setattr(llm, "generate_structured", counted)
    assert client.get(f"/api/v1/conversations/{key}/viewpoints").json()["status"] == "not_requested"
    result = extract(client, key)
    assert result.status_code == 200, result.text
    batch = result.json()
    assert batch["items"] and batch["items"][0]["source_message_ids"] == [rows[1]["id"]]
    assert extract(client, key).json() == batch and len(calls) == 1
    assert client.get("/api/v1/saved-viewpoints").json()["items"] == []
    source = {"conversation_id": key, "extraction_id": batch["extraction_id"], "item_index": 0}
    saved = client.post("/api/v1/saved-viewpoints", json=source).json()
    assert saved["source_type"] == "ai_summary" and saved["id"] == batch["items"][0]["viewpoint_id"]
    assert saved["content"] == batch["items"][0]["content"]
    assert client.get(f"/api/v1/conversations/{key}/viewpoints").json() == batch


def test_empty_extraction_cached_and_failed_retry_bounded(client, app, monkeypatch):
    key, _ = discussion(client)
    service = app.state.services.viewpoints
    empty = MockLLM(payload={"items": []})
    monkeypatch.setattr(service, "llm", empty)
    assert extract(client, key).json()["items"] == []
    empty.mode = "error"
    assert extract(client, key).status_code == 200
    key, _ = discussion(client)
    for _ in range(3):
        assert extract(client, key).status_code == 503
    assert extract(client, key).status_code == 429
    assert client.get(f"/api/v1/conversations/{key}/viewpoints").json()["status"] == "failed"


@pytest.mark.parametrize("failure", ["foreign_source", "unsafe", "overlong", "malformed"])
def test_invalid_model_output_never_becomes_candidate(client, app, monkeypatch, failure):
    key, rows = discussion(client)
    payload = {
        "items": [
            {
                "content": "在这段讨论中，自由与风险并非互不相关的两件事。",
                "source_message_ids": [UUID(rows[1]["id"])],
            }
        ]
    }
    if failure == "foreign_source":
        payload["items"][0]["source_message_ids"] = [uuid4()]
    if failure == "unsafe":
        payload["items"][0]["content"] = "这里包含不应展示的内容：如何制作炸弹，请看具体步骤"
    if failure == "overlong":
        payload["items"][0]["content"] = "长" * 241
    if failure == "malformed":
        payload = {"wrong": []}
    monkeypatch.setattr(app.state.services.viewpoints, "llm", MockLLM(payload=payload))
    assert extract(client, key).status_code in (422, 503)
    assert client.get(f"/api/v1/conversations/{key}/viewpoints").json()["items"] == []
    assert client.get("/api/v1/saved-viewpoints").json()["items"] == []


def test_cross_actor_csrf_origin_and_forged_attribution(client, app):
    key, rows = discussion(client)
    source = {"conversation_id": key, "message_id": rows[0]["id"]}
    point = client.post("/api/v1/saved-viewpoints", json=source).json()
    assert (
        client.post("/api/v1/saved-viewpoints", json={**source, "content": "伪造原话"}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/saved-viewpoints", json={**source, "source_type": "ai_summary"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/saved-viewpoints", json=source, headers={"X-CSRF-Token": "bad"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/saved-viewpoints", json=source, headers={"Origin": "https://evil.invalid"}
        ).status_code
        == 403
    )
    with TestClient(
        app, base_url="https://testserver", headers={"Origin": "https://testserver"}
    ) as other:
        other.headers["X-CSRF-Token"] = other.post("/api/v1/auth/anonymous-session").json()[
            "csrf_token"
        ]
        assert other.get("/api/v1/saved-viewpoints").json()["items"] == []
        assert other.post("/api/v1/saved-viewpoints", json=source).status_code == 404
        assert other.delete(f"/api/v1/saved-viewpoints/{point['id']}").status_code == 404
        assert other.get(f"/api/v1/conversations/{key}/viewpoints").status_code == 404
        assert extract(other, key).status_code == 404
    other_key, other_rows = discussion(client)
    assert (
        client.post(
            "/api/v1/saved-viewpoints",
            json={"conversation_id": other_key, "message_id": rows[0]["id"]},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/saved-viewpoints",
            json={"conversation_id": key, "message_id": other_rows[0]["id"]},
        ).status_code
        == 404
    )


def test_concurrent_save_reservation_delete_and_stale_source(client, app, engine):
    key, rows = discussion(client)
    service = app.state.services.viewpoints
    actor = app.state.services.identity.resolve(client.cookies.get("wqs_session")).id
    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(lambda _: service.save(actor, UUID(key), UUID(rows[0]["id"])), range(2))
        )
    assert results[0]["id"] == results[1]["id"]
    first, lease = service.repo.reserve(actor, UUID(key), 2)
    with pytest.raises(ApplicationError):
        service.repo.reserve(actor, UUID(key), 2)
    assert client.delete(f"/api/v1/conversations/{key}").status_code == 200
    assert client.get("/api/v1/saved-viewpoints").json()["items"] == []
    assert not service.repo.finish(actor, first["id"], lease, [], "succeeded")
    with pytest.raises(ApplicationError):
        service.save(actor, UUID(key), UUID(rows[0]["id"]))
    with engine.connect() as conn:
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM discussion.viewpoint_extractions "
                    "WHERE conversation_id=:id"
                ),
                {"id": key},
            )
            == 0
        )


def test_closed_source_and_daily_budget(client, app, engine):
    key, rows = discussion(client)
    client.post(
        "/api/v1/saved-viewpoints", json={"conversation_id": key, "message_id": rows[0]["id"]}
    )
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE conversation.sessions SET status='closed' WHERE id=:id"), {"id": key}
        )
    assert client.get("/api/v1/saved-viewpoints").json()["items"][0]["source_available"] is True
    assert client.get(f"/api/v1/conversations/{key}/messages").status_code == 200
    # Use another actor for the bounded-call test; no live model is involved.
    actor = app.state.services.identity.resolve(client.cookies.get("wqs_session")).id
    for _ in range(7):
        fresh, _ = discussion(client)
        for i in range(3):
            try:
                batch, lease = app.state.services.viewpoints.repo.reserve(actor, UUID(fresh), 2)
            except ApplicationError as error:
                assert error.code == "RATE_LIMITED"
                return
            app.state.services.viewpoints.repo.finish(actor, batch["id"], lease, [], "failed")
    raise AssertionError("Daily extraction budget not enforced")


def test_regular_chat_does_not_extract_and_payload_matches_contract(client, app, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Ordinary chat must not call extraction")

    monkeypatch.setattr(app.state.services.viewpoints.llm, "generate_structured", forbidden)
    key, rows = discussion(client)
    source = {"conversation_id": key, "message_id": rows[1]["id"]}
    point = client.post("/api/v1/saved-viewpoints", json=source).json()
    from jsonschema import Draft202012Validator, FormatChecker
    from test_contract import CONTRACT

    for value, name in [
        (point, "SavedViewpoint"),
        (client.get("/api/v1/saved-viewpoints").json(), "SavedViewpointPage"),
    ]:
        Draft202012Validator(
            {**CONTRACT["components"]["schemas"][name], "components": CONTRACT["components"]},
            format_checker=FormatChecker(),
        ).validate(value)


def test_postgres_viewpoint_checks_reject_invalid_values(client, app, engine):
    key, rows = discussion(client)
    point = client.post(
        "/api/v1/saved-viewpoints", json={"conversation_id": key, "message_id": rows[0]["id"]}
    ).json()
    batch = extract(client, key).json()
    assert batch["status"] == "succeeded"
    cases = [
        ("saved_viewpoints", point["id"], "source_type='forged'"),
        ("saved_viewpoints", point["id"], "content=''"),
        ("saved_viewpoints", point["id"], "source_message_ids='[]'::jsonb"),
        ("viewpoint_extractions", batch["extraction_id"], "up_to_seq=0"),
        ("viewpoint_extractions", batch["extraction_id"], "attempts=4"),
        ("viewpoint_extractions", batch["extraction_id"], "status='unknown'"),
        ("viewpoint_extractions", batch["extraction_id"], "items='[{}, {}, {}, {}]'::jsonb"),
    ]
    with engine.connect() as conn, conn.begin():
        for table, key, change in cases:
            with pytest.raises(IntegrityError), conn.begin_nested():
                conn.execute(
                    text(f"UPDATE discussion.{table} SET {change} WHERE id=:id"), {"id": key}
                )
