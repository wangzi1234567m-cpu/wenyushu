import copy
from dataclasses import replace
from datetime import UTC, datetime

import pytest
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
