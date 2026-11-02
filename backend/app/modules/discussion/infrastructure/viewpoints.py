from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

from app.modules.discussion.infrastructure.models import contexts_table as contexts
from app.modules.discussion.infrastructure.models import extractions_table as batches
from app.modules.discussion.infrastructure.models import saved_viewpoints_table as saved
from app.shared.errors import ApplicationError
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert


class SqlViewpoints:
    def __init__(self, factory):
        self.factory = factory

    def batch(self, actor, key=None, conversation=None):
        with self.factory() as s:
            q = select(batches).where(batches.c.actor_id == actor)
            q = (
                q.where(batches.c.id == key)
                if key
                else q.where(batches.c.conversation_id == conversation)
            )
            row = s.execute(q.order_by(batches.c.up_to_seq.desc()).limit(1)).mappings().first()
            return dict(row) if row else None

    def _lock_source(self, s, actor, conversation, guard=None):
        row = s.execute(
            select(contexts.c.id)
            .where(contexts.c.actor_id == actor, contexts.c.conversation_id == conversation)
            .with_for_update()
        ).first()
        if not row:
            raise ApplicationError("NOT_FOUND", "原讨论已不可用")
        if guard:
            guard()

    def reserve(self, actor, conversation, up_to_seq, guard=None):
        now = datetime.now(UTC)
        key = uuid5(NAMESPACE_URL, f"wqs:extraction:{actor}:{conversation}:{up_to_seq}")
        with self.factory.begin() as s:
            s.execute(text("SELECT pg_advisory_xact_lock(914027)"))
            self._lock_source(s, actor, conversation, guard)
            row = (
                s.execute(select(batches).where(batches.c.id == key).with_for_update())
                .mappings()
                .first()
            )
            if row and row["status"] == "succeeded":
                return dict(row), None
            if (
                row
                and row["status"] == "processing"
                and row["updated_at"] > now - timedelta(seconds=90)
            ):
                raise ApplicationError("CONVERSATION_BUSY", "这段讨论的观点正在整理，请稍候", True)
            if row and row["attempts"] >= 3:
                raise ApplicationError(
                    "RATE_LIMITED", "这段讨论已达到重试上限，可以继续讨论后再提炼", False
                )
            count = select(func.coalesce(func.sum(batches.c.attempts), 0)).where(
                batches.c.updated_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
            )
            if s.scalar(count) >= 200 or s.scalar(count.where(batches.c.actor_id == actor)) >= 20:
                raise ApplicationError("RATE_LIMITED", "今日观点提炼次数已达上限", True)
            lease = uuid4()
            if row:
                s.execute(
                    update(batches)
                    .where(batches.c.id == key)
                    .values(
                        status="processing",
                        lease_id=lease,
                        attempts=row["attempts"] + 1,
                        updated_at=now,
                    )
                )
            else:
                s.execute(
                    insert(batches).values(
                        id=key,
                        actor_id=actor,
                        conversation_id=conversation,
                        up_to_seq=up_to_seq,
                        status="processing",
                        lease_id=lease,
                        attempts=1,
                        items=[],
                        created_at=now,
                        updated_at=now,
                    )
                )
            return {"id": key, "up_to_seq": up_to_seq}, lease

    def finish(self, actor, key, lease, items, status):
        with self.factory.begin() as s:
            return (
                s.execute(
                    update(batches)
                    .where(
                        batches.c.id == key,
                        batches.c.actor_id == actor,
                        batches.c.lease_id == lease,
                    )
                    .values(items=items, status=status, lease_id=None, updated_at=datetime.now(UTC))
                ).rowcount
                == 1
            )

    def save(self, values, guard):
        with self.factory.begin() as s:
            self._lock_source(s, values["actor_id"], values["conversation_id"], guard)
            s.execute(insert(saved).values(**values).on_conflict_do_nothing())
            return dict(
                s.execute(
                    select(saved).where(
                        saved.c.id == values["id"], saved.c.actor_id == values["actor_id"]
                    )
                )
                .mappings()
                .one()
            )

    def list(self, actor, limit, offset, conversation=None):
        with self.factory() as s:
            q = select(saved).where(saved.c.actor_id == actor)
            if conversation:
                q = q.where(saved.c.conversation_id == conversation)
            return [
                dict(r)
                for r in s.execute(
                    q.order_by(saved.c.created_at.desc(), saved.c.id.desc())
                    .offset(offset)
                    .limit(limit + 1)
                ).mappings()
            ]

    def remove(self, actor, key):
        with self.factory.begin() as s:
            if not s.execute(
                delete(saved).where(saved.c.id == key, saved.c.actor_id == actor)
            ).rowcount:
                raise ApplicationError("NOT_FOUND", "收藏不存在")

    def purge(self, actor, conversation):
        with self.factory.begin() as s:
            s.execute(
                select(contexts.c.id)
                .where(contexts.c.actor_id == actor, contexts.c.conversation_id == conversation)
                .with_for_update()
            ).first()
            s.execute(
                delete(saved).where(
                    saved.c.actor_id == actor, saved.c.conversation_id == conversation
                )
            )
            s.execute(
                delete(batches).where(
                    batches.c.actor_id == actor, batches.c.conversation_id == conversation
                )
            )
