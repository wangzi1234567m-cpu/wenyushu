from datetime import timedelta
from uuid import uuid4

import pytest
from app.shared.errors import ApplicationError
from fastapi.testclient import TestClient

PATH = "/api/v1/auth/anonymous-session"


def test_bootstrap_idempotency_cookie_and_hash(client, foundation):
    first = client.post(PATH)
    assert first.status_code == 201
    token = client.cookies.get("wqs_session")
    assert len(token) >= 43
    assert all(
        p in first.headers["set-cookie"] for p in ("HttpOnly", "Secure", "SameSite=lax", "Path=/")
    )
    actor = foundation[1].identity.resolve(token)
    assert actor.token_hash != token
    second = client.post(PATH)
    assert second.status_code == 201
    assert client.cookies.get("wqs_session") == token
    assert len(foundation[2]) == 1
    assert second.json()["csrf_token"] != first.json()["csrf_token"]
    # Older CSRF token remains usable across tabs.
    assert (
        client.delete(PATH, headers={"X-CSRF-Token": first.json()["csrf_token"]}).status_code == 200
    )
    with pytest.raises(ApplicationError, match="匿名凭证"):
        foundation[1].identity.resolve(token)


@pytest.mark.parametrize("origin", ["https://evil.example", "null", "https://testserver.evil", ""])
def test_origin_rejected(client, origin):
    response = client.post(PATH, headers={"Origin": origin})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORIGIN_REJECTED"


def test_missing_origin(foundation):
    with TestClient(foundation[0], base_url="https://testserver") as c:
        assert c.post(PATH).status_code == 403


def test_csrf_missing_bad_and_cross_actor(client, foundation):
    first = client.post(PATH).json()["csrf_token"]
    assert client.delete(PATH).status_code == 422
    assert client.delete(PATH, headers={"X-CSRF-Token": "bad"}).status_code == 403
    with TestClient(
        foundation[0], base_url="https://testserver", headers={"Origin": "https://testserver"}
    ) as other:
        second = other.post(PATH).json()["csrf_token"]
        assert other.delete(PATH, headers={"X-CSRF-Token": first}).status_code == 403
        assert client.delete(PATH, headers={"X-CSRF-Token": second}).status_code == 403
        assert other.delete(PATH, headers={"X-CSRF-Token": second}).status_code == 200


def test_expiration_and_invalid_cookie(client, foundation):
    client.cookies.set("wqs_session", "invalid")
    assert client.post(PATH).status_code == 201
    client.cookies.clear()
    client.post(PATH)
    old = client.cookies.get("wqs_session")
    foundation[3][0] += timedelta(days=7)
    with pytest.raises(ApplicationError):
        foundation[1].identity.resolve(old)
    assert client.post(PATH).status_code == 201
    assert client.cookies.get("wqs_session") != old


def test_csrf_boundary(client, foundation):
    token = client.post(PATH).json()["csrf_token"]
    foundation[3][0] += timedelta(hours=1)
    assert client.delete(PATH, headers={"X-CSRF-Token": token}).status_code == 403


def test_owner_and_missing_resource_same_failure(client, foundation):
    client.post(PATH)
    actor = foundation[1].identity.resolve(client.cookies.get("wqs_session"))
    auth = foundation[1].authorization
    auth.require_owner(actor, actor.id)
    for owner in (None, uuid4()):
        with pytest.raises(ApplicationError) as error:
            auth.require_owner(actor, owner)
        assert error.value.code == "NOT_FOUND"


def test_failed_commit_no_cookie_or_private_error(client, foundation, caplog):
    foundation[4]["fail_commit"] = True
    response = client.post(PATH)
    assert response.status_code == 500
    assert "set-cookie" not in response.headers
    assert not foundation[2]
    assert "private database password" not in response.text + caplog.text
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


def test_health_and_body_limits(client, foundation):
    assert client.get("/api/v1/health/live").json() == {"status": "ok"}
    assert client.get("/api/v1/health/ready").status_code == 200
    foundation[4]["ready"] = False
    assert client.get("/api/v1/health/ready").status_code == 503
    assert client.get("/api/v1/health/live").status_code == 200
    assert client.post(PATH, content=b"x" * 65536).status_code == 201
    assert client.post(PATH, content=b"x" * 65537).status_code == 422
    assert client.post(PATH, content=iter([b"x" * 32768, b"x" * 32769])).status_code == 422
    assert client.post("/api/v1/recommendations").status_code == 404


def test_unauthorized_revoke(client):
    assert client.delete(PATH, headers={"X-CSRF-Token": "x"}).status_code == 401
