from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.shared.errors import ApplicationError


@dataclass(frozen=True)
class Actor:
    id: UUID
    token_hash: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None

    def valid_at(self, now: datetime) -> bool:
        return self.revoked_at is None and self.created_at <= now < self.expires_at


class OwnerAuthorization:
    def require_owner(self, actor: Actor, owner_id: UUID | None) -> None:
        if owner_id is None or actor.id != owner_id:
            raise ApplicationError("NOT_FOUND", "资源不存在")
