import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.identity.application.ports import CsrfPort, IdentityUnitOfWork
from app.modules.identity.domain.actor import Actor
from app.shared.errors import ApplicationError


def utcnow() -> datetime:
    return datetime.now(UTC)


def credential_hash(credential: str) -> str:
    return hashlib.sha256(credential.encode()).hexdigest()


@dataclass(frozen=True)
class SessionResult:
    credential: str
    expires_at: datetime
    csrf_token: str


class IdentityService:
    def __init__(
        self,
        uow: Callable[[], IdentityUnitOfWork],
        csrf: CsrfPort,
        lifetime_seconds: int = 604800,
        clock: Callable[[], datetime] = utcnow,
    ):
        self.uow = uow
        self.csrf = csrf
        self.lifetime_seconds = lifetime_seconds
        self.clock = clock

    def bootstrap(self, credential: str | None) -> SessionResult:
        now = self.clock()
        with self.uow() as work:
            actor = work.actors.find(credential_hash(credential)) if credential else None
            if actor is None or not actor.valid_at(now):
                credential = secrets.token_urlsafe(32)
                actor = Actor(
                    uuid4(),
                    credential_hash(credential),
                    now,
                    now + timedelta(seconds=self.lifetime_seconds),
                )
                work.actors.add(actor)
            work.commit()
        assert credential is not None
        return SessionResult(credential, actor.expires_at, self.csrf.issue(credential, now))

    def resolve(self, credential: str | None) -> Actor:
        if credential:
            with self.uow() as work:
                actor = work.actors.find(credential_hash(credential))
                if actor and actor.valid_at(self.clock()):
                    return actor
        raise ApplicationError("UNAUTHORIZED", "匿名凭证缺失或失效")

    def revoke(self, credential: str | None, csrf_token: str | None) -> None:
        actor = self.resolve(credential)
        assert credential is not None
        if not self.csrf.verify(csrf_token, credential, self.clock()):
            raise ApplicationError("CSRF_REJECTED", "请求验证失败")
        with self.uow() as work:
            work.actors.revoke(actor.id, self.clock())
            work.commit()
