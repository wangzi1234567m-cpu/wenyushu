import copy
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.bootstrap.container import Services
from app.infrastructure.settings.config import Settings
from app.integrations.llm.mock import MockLLM
from app.integrations.search.mock import MockSearch
from app.main import create_app
from app.modules.identity.application.service import IdentityService
from app.modules.identity.domain.actor import OwnerAuthorization
from app.modules.identity.infrastructure.csrf import SignedCsrf
from app.shared.health import HealthService
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url


class MemoryUow:
    def __init__(self, store, fail=False):
        self.store = store
        self.fail = fail

    def __enter__(self):
        self.local = copy.deepcopy(self.store)
        self.actors = self
        return self

    def find(self, token_hash):
        return self.local.get(token_hash)

    def add(self, actor):
        self.local[actor.token_hash] = actor

    def revoke(self, actor_id, now):
        for key, actor in self.local.items():
            if actor.id == actor_id:
                self.local[key] = replace(actor, revoked_at=now)

    def commit(self):
        if self.fail:
            raise RuntimeError("private database password")
        self.store.clear()
        self.store.update(self.local)

    def __exit__(self, *args):
        pass


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        provider="mock",
        database_url="postgresql+psycopg://test:test@localhost/wqs_test",
        csrf_secret="test-only-secret-which-is-not-for-production",
        allowed_origins=["https://testserver"],
        environment="test",
    )


@pytest.fixture
def foundation(settings):
    store = {}
    clock = [datetime.now(UTC)]
    flags = {"ready": True, "fail_commit": False}
    identity = IdentityService(
        lambda: MemoryUow(store, flags["fail_commit"]),
        SignedCsrf(settings.csrf_secret.get_secret_value()),
        clock=lambda: clock[0],
    )
    services = Services(
        identity,
        HealthService(lambda: flags["ready"]),
        OwnerAuthorization(),
        MockLLM(),
        MockSearch(),
    )
    app = create_app(settings, services)
    return app, services, store, clock, flags


@pytest.fixture
def client(foundation):
    with TestClient(
        foundation[0],
        base_url="https://testserver",
        raise_server_exceptions=False,
        headers={"Origin": "https://testserver"},
    ) as client:
        yield client


ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="module")
def engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not configured; PostgreSQL acceptance not passed")
    assert make_url(url).database.endswith("_test"), "Refusing non-test database"
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    config = Config(str(ROOT / "backend/alembic.ini"))
    db = create_engine(url, connect_args={"connect_timeout": 3})
    # Existing business schemas must not be overwritten.
    with db.connect() as conn:
        schemas = inspect(conn).get_schema_names()
        assert not set(schemas) & {
            "identity",
            "content",
            "conversation",
            "discussion",
            "reading",
            "catalog",
            "handoff",
            "safety",
        }, "Tests require an empty disposable database"
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    yield db
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    db.dispose()
    if old is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = old
