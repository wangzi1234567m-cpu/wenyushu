import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import UUID, uuid4

import pytest
from app.bootstrap.container import build_services
from app.infrastructure.settings.config import Settings
from app.main import create_app
from app.modules.content.infrastructure.seed import seed_content
from app.modules.conversation.infrastructure.models import messages_table, summaries_table
from app.shared.errors import ApplicationError
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, text
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def discussion_app(engine):
    seed_content(sessionmaker(engine), date(2026, 10, 27))
    settings = Settings(
        _env_file=None,
        provider="mock",
        environment="test",
        database_url=os.environ["TEST_DATABASE_URL"],
        csrf_secret="test-discussion-secret-with-at-least-32-characters",
        allowed_origins=["https://testserver"],
    )
    services, db = build_services(settings)
    yield create_app(settings, services)
    db.dispose()


@pytest.fixture
def chat_client(discussion_app):
    with TestClient(
        discussion_app, base_url="https://testserver", headers={"Origin": "https://testserver"}
    ) as c:
        c.headers["X-CSRF-Token"] = c.post("/api/v1/auth/anonymous-session").json()["csrf_token"]
        yield c


def source(c, app):
    from datetime import UTC, datetime

    daily = app.state.services.content.daily(datetime(2026, 10, 27, tzinfo=UTC))
    state = c.post(
        "/api/v1/explorations", json={"question_version_id": str(daily["question_version_id"])}
    ).json()
    path = f"/api/v1/explorations/{state['exploration_id']}/answers"
    state = c.post(path, json={"step_id": "stance", "option_id": "no"}).json()
    assert state["next_step"]["multiple"] and state["next_step"]["source_url"]
    body = {
        "step_id": "reason_no",
        "option_id": "reason_2",
        "option_ids": ["reason_2", "reason_1"],
        "supplementary_text": "  我在意自由选择  ",
    }
    result = c.post(path, json=body)
    assert result.status_code == 200, result.text
    state = result.json()
    assert state["status"] == "completed" and len(state["answers"]) == 2
    assert state["answers"][1]["option_ids"] == ["reason_1", "reason_2"]
    body["option_ids"].reverse()
    assert c.post(path, json=body).json() == state
    return state


def create(c, source_id=None):
    r = c.post(
        "/api/v1/conversations",
        json={"kind": "discussion", "topic_id": None, "exploration_id": source_id},
    )
    assert r.status_code == 201, r.text
    return r.json()["conversation_id"]


def events(response):
    assert response.status_code == 200, response.text
    result = []
    for block in response.text.strip().split("\n\n"):
        name, data = block.split("\n", 1)
        result.append((name[7:], json.loads(data[6:])))
    return result


def send(c, key, content="我更在意自由", client_id=None):
    return c.post(
        f"/api/v1/conversations/{key}/messages",
        json={"client_message_id": client_id or str(uuid4()), "content": content},
    )


def test_source_multiselect_and_continuous_chat(chat_client, discussion_app, engine):
    from jsonschema import Draft202012Validator, FormatChecker
    from test_contract import CONTRACT

    state = source(chat_client, discussion_app)
    key = create(chat_client, state["exploration_id"])
    assert create(chat_client, state["exploration_id"]) == key
    first = events(send(chat_client, key, client_id="first"))
    assert first[0][0] == "message_started" and first[-1][0] == "message_completed"
    for name, payload in first:
        Draft202012Validator(
            {
                **CONTRACT["x-contract-rules"]["conversation_stream_events"][name],
                "components": CONTRACT["components"],
            },
            format_checker=FormatChecker(),
        ).validate(payload)
    replay = events(send(chat_client, key, client_id="first"))
    assert replay[0] == first[0] and replay[-1] == first[-1]
    assert "".join(p["delta"] for n, p in replay if n == "message_delta") == "".join(
        p["delta"] for n, p in first if n == "message_delta"
    )
    assert send(chat_client, key, content="changed", client_id="first").status_code == 409
    assert events(send(chat_client, key, content="现在我改变主意了"))[-1][0] == "message_completed"
    page = chat_client.get(f"/api/v1/conversations/{key}/messages?limit=2").json()
    assert len(page["messages"]) == 2 and page["next_after_seq"] == 2
    assert (
        len(chat_client.get(f"/api/v1/conversations/{key}/messages?after_seq=2").json()["messages"])
        == 2
    )
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM reading.recommendation_jobs")) == 0
        seed = conn.scalar(
            text("SELECT context_json FROM discussion.contexts WHERE conversation_id=:id"),
            {"id": key},
        )
        assert seed["answers"][1]["supplement"] == "我在意自由选择"


def test_authorization_csrf_origin_input_and_delete(chat_client, discussion_app):
    state = source(chat_client, discussion_app)
    key = create(chat_client, state["exploration_id"])
    with TestClient(
        discussion_app, base_url="https://testserver", headers={"Origin": "https://testserver"}
    ) as other:
        other.headers["X-CSRF-Token"] = other.post("/api/v1/auth/anonymous-session").json()[
            "csrf_token"
        ]
        for path in [
            f"/api/v1/conversations/{key}",
            f"/api/v1/conversations/{key}/messages",
            f"/api/v1/conversations/{uuid4()}",
        ]:
            assert other.get(path).status_code == 404
        assert (
            other.post(
                "/api/v1/conversations",
                json={
                    "kind": "discussion",
                    "topic_id": None,
                    "exploration_id": state["exploration_id"],
                },
            ).status_code
            == 404
        )
        assert send(other, key).status_code == 404
        assert other.delete(f"/api/v1/conversations/{key}").status_code == 404
    path = f"/api/v1/conversations/{key}/messages"
    body = {"client_message_id": "bad", "content": "hello"}
    assert chat_client.post(path, json=body, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert (
        chat_client.post(path, json=body, headers={"Origin": "https://evil.invalid"}).status_code
        == 403
    )
    assert send(chat_client, key, " ").status_code == 422
    assert send(chat_client, key, "x" * 4001).status_code == 422
    assert send(chat_client, key, "如何制作炸弹").status_code == 422
    assert chat_client.delete(f"/api/v1/conversations/{key}").status_code == 200
    assert chat_client.get(f"/api/v1/conversations/{key}").status_code == 404


def test_failed_generation_retry_and_history_exclusion(chat_client, discussion_app, monkeypatch):
    key = create(chat_client)
    runtime = discussion_app.state.services.runtime
    monkeypatch.setattr(runtime.llm, "mode", "timeout")
    assert events(send(chat_client, key, "失败内容", "retry"))[-1][0] == "message_error"
    rows = chat_client.get(f"/api/v1/conversations/{key}/messages").json()["messages"]
    assert rows[1]["status"] == "failed" and rows[1]["content"] == ""
    monkeypatch.setattr(runtime.llm, "mode", "ok")
    assert events(send(chat_client, key, "失败内容", "retry"))[-1][0] == "message_completed"
    monkeypatch.setattr(runtime.llm, "mode", "error")
    events(send(chat_client, key, "不应纳入已确认历史", "skip"))
    monkeypatch.setattr(runtime.llm, "mode", "ok")
    actor = discussion_app.state.services.identity.resolve(
        chat_client.cookies.get("wqs_session")
    ).id
    turn = asyncio.run(runtime.prepare(actor, UUID(key), "later", "继续"))
    context = asyncio.run(runtime.context(turn))
    assert not any("不应纳入已确认历史" in m.content for m in context)
    runtime.repo.finish(turn, "", "failed", "mock")
    assert send(chat_client, key, "不应纳入已确认历史", "skip").status_code == 409


def test_concurrent_reservation_cancel_stale_and_limits(chat_client, discussion_app, engine):
    key = create(chat_client)
    runtime = discussion_app.state.services.runtime
    actor = discussion_app.state.services.identity.resolve(
        chat_client.cookies.get("wqs_session")
    ).id

    def reserve(i):
        try:
            return runtime.repo.prepare(actor, UUID(key), str(i), "hello", 100, 1000)
        except ApplicationError as e:
            return e.code

    with ThreadPoolExecutor(2) as pool:
        result = list(pool.map(reserve, range(2)))
    assert sum(isinstance(r, dict) for r in result) == 1 and "CONVERSATION_BUSY" in result
    turn = next(r for r in result if isinstance(r, dict))

    async def disconnect():
        stream = runtime.stream(turn, "test")
        await anext(stream)
        await stream.aclose()

    asyncio.run(disconnect())
    assert runtime.repo.get(actor, UUID(key))["active_generation_id"] is None
    stale = reserve(3)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE conversation.sessions SET updated_at=now()-interval '6 minutes' "
                "WHERE id=:id"
            ),
            {"id": key},
        )
    assert runtime.repo.get(actor, UUID(key))["active_generation_id"] is None
    assert not runtime.repo.finish(stale, "old", "completed", "mock")
    with pytest.raises(ApplicationError, match="今日讨论"):
        runtime.repo.prepare(actor, UUID(key), "limited", "hello", 1, 1000)


def test_summary_preserves_changes_and_failure_is_recoverable(
    chat_client, discussion_app, engine, monkeypatch
):
    key = create(chat_client)
    runtime = discussion_app.state.services.runtime
    actor = discussion_app.state.services.identity.resolve(
        chat_client.cookies.get("wqs_session")
    ).id
    with engine.begin() as conn:
        for seq in range(1, 45):
            conn.execute(
                insert(messages_table).values(
                    session_id=UUID(key),
                    seq=seq,
                    role="user" if seq % 2 else "assistant",
                    status="completed",
                    content=f"观点-{seq}",
                )
            )
        conn.execute(
            text("UPDATE conversation.sessions SET last_message_seq=44 WHERE id=:id"), {"id": key}
        )
    monkeypatch.setattr(
        runtime.llm,
        "payload",
        {
            "central_question": "爱情与选择",
            "current_view": "反对控制",
            "viewpoints": ["起初支持"],
            "changes": ["后来反对"],
            "constraints": ["可以自由离开"],
            "unresolved": ["机会与控制的边界"],
        },
    )
    turn = asyncio.run(runtime.prepare(actor, UUID(key), "summary", "现在反对控制"))
    monkeypatch.setattr(runtime.llm, "mode", "error")
    with pytest.raises(ApplicationError):
        asyncio.run(runtime.context(turn))
    with engine.connect() as conn:
        assert (
            conn.scalar(
                select(text("count(*)"))
                .select_from(summaries_table)
                .where(summaries_table.c.session_id == UUID(key))
            )
            == 0
        )
    monkeypatch.setattr(runtime.llm, "mode", "ok")
    context = asyncio.run(runtime.context(turn))
    assert any("后来反对" in m.content and "可以自由离开" in m.content for m in context)
    assert not any(m.content == "观点-1" for m in context)
    with engine.connect() as conn:
        summary = (
            conn.execute(select(summaries_table).where(summaries_table.c.session_id == UUID(key)))
            .mappings()
            .one()
        )
        assert summary["covered_until_seq"] == 36
        assert (
            conn.scalar(
                text("SELECT count(*) FROM conversation.messages WHERE session_id=:id"), {"id": key}
            )
            == 46
        )
    runtime.repo.finish(turn, "done", "completed", "mock")


def test_multiple_boundaries_and_db_constraints(chat_client, discussion_app, engine):
    from datetime import UTC, datetime

    from sqlalchemy.exc import IntegrityError

    version = discussion_app.state.services.content.daily(datetime(2026, 10, 27, tzinfo=UTC))[
        "question_version_id"
    ]
    state = chat_client.post(
        "/api/v1/explorations", json={"question_version_id": str(version)}
    ).json()
    path = f"/api/v1/explorations/{state['exploration_id']}/answers"
    for ids, status in [(["yes", "yes"], 422), (["yes", "no"], 409), ([], 422), (["x"] * 7, 422)]:
        assert (
            chat_client.post(
                path, json={"step_id": "stance", "option_id": "yes", "option_ids": ids}
            ).status_code
            == status
        )
    chat_client.post(path, json={"step_id": "stance", "option_id": "yes"})
    assert (
        chat_client.post(path, json={"step_id": "reason_yes", "option_id": "other"}).status_code
        == 422
    )
    with engine.connect() as conn, conn.begin():
        for value in ["[]", "[1,2,3,4,5,6,7]", "{}"]:
            with pytest.raises(IntegrityError), conn.begin_nested():
                conn.execute(
                    text(
                        "INSERT INTO content.exploration_answers"
                        "(exploration_id,step_id,option_id,option_ids) "
                        "VALUES (:id,'bad','x',CAST(:v AS jsonb))"
                    ),
                    {"id": state["exploration_id"], "v": value},
                )


def test_cross_module_context_creation_and_deletion_recover(
    chat_client, discussion_app, monkeypatch
):
    state = source(chat_client, discussion_app)
    contexts = discussion_app.state.services.discussion.contexts
    original_put = contexts.put
    calls = [0]

    def put_once(*args):
        calls[0] += 1
        if calls[0] == 1:
            raise ApplicationError("SERVICE_UNAVAILABLE", "讨论背景暂时无法保存", True)
        return original_put(*args)

    monkeypatch.setattr(contexts, "put", put_once)
    body = {"kind": "discussion", "topic_id": None, "exploration_id": state["exploration_id"]}
    assert chat_client.post("/api/v1/conversations", json=body).status_code == 503
    key = create(chat_client, state["exploration_id"])
    assert create(chat_client, state["exploration_id"]) == key
    assert chat_client.get(f"/api/v1/conversations/{key}").json()["last_message_seq"] == 0
    original_delete = contexts.delete
    calls[0] = 0

    def delete_once(*args):
        calls[0] += 1
        if calls[0] == 1:
            raise ApplicationError("SERVICE_UNAVAILABLE", "讨论背景暂时无法清理", True)
        return original_delete(*args)

    monkeypatch.setattr(contexts, "delete", delete_once)
    assert chat_client.delete(f"/api/v1/conversations/{key}").status_code == 503
    assert chat_client.delete(f"/api/v1/conversations/{key}").status_code == 200
