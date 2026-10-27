from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.modules.identity.domain.actor import Actor
from app.modules.identity.infrastructure.models import ActorRow


class SqlActorRepository:
    def __init__(self, session: Session):
        self.session = session

    def find(self, token_hash: str) -> Actor | None:
        row = self.session.scalar(select(ActorRow).where(ActorRow.token_hash == token_hash))
        if row is None:
            return None
        return Actor(
            row.id,
            row.token_hash,
            row.created_at.astimezone(UTC),
            row.expires_at.astimezone(UTC),
            row.revoked_at.astimezone(UTC) if row.revoked_at else None,
        )

    def add(self, actor: Actor) -> None:
        self.session.add(
            ActorRow(
                id=actor.id,
                token_hash=actor.token_hash,
                created_at=actor.created_at,
                expires_at=actor.expires_at,
            )
        )

    def revoke(self, actor_id: UUID, now: datetime) -> None:
        self.session.execute(update(ActorRow).where(ActorRow.id == actor_id).values(revoked_at=now))


class SqlIdentityUnitOfWork:
    def __init__(self, factory: sessionmaker):
        self.factory = factory

    def __enter__(self):
        self.session = self.factory()
        self.actors = SqlActorRepository(self.session)
        return self

    def commit(self) -> None:
        self.session.commit()

    def __exit__(self, *args: object) -> None:
        self.session.rollback()
        self.session.close()
