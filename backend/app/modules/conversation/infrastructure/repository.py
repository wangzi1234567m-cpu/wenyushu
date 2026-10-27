from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.modules.conversation.infrastructure.models import messages_table as messages
from app.modules.conversation.infrastructure.models import sessions_table as sessions
from app.modules.conversation.infrastructure.models import summaries_table as summaries
from app.shared.errors import ApplicationError


class SqlConversationRepository:
    def __init__(self, factory):
        self.factory = factory

    def _owned(self, s, actor, key, lock=False):
        q = select(sessions).where(sessions.c.id == key, sessions.c.actor_id == actor)
        row = s.execute(q.with_for_update() if lock else q).mappings().first()
        if not row:
            raise ApplicationError("NOT_FOUND", "资源不存在")
        row = dict(row)
        now = datetime.now(UTC)
        if row["expires_at"] and row["expires_at"] <= now:
            row["status"] = "expired"
        if row["active_generation_id"] and row["updated_at"] < now - timedelta(minutes=5) and lock:
            s.execute(
                update(messages)
                .where(messages.c.session_id == key, messages.c.status == "generating")
                .values(status="failed")
            )
            s.execute(
                update(sessions).where(sessions.c.id == key).values(active_generation_id=None)
            )
            row["active_generation_id"] = None
        return row

    def create(self, actor_id, conversation_id, topic_id):
        with self.factory.begin() as s:
            s.execute(
                pg_insert(sessions)
                .values(
                    id=conversation_id,
                    actor_id=actor_id,
                    topic_id=topic_id,
                    policy_version="discussion-v1",
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                )
                .on_conflict_do_nothing()
            )
            return self._owned(s, actor_id, conversation_id)

    def get(self, actor_id, conversation_id):
        with self.factory.begin() as s:
            return self._owned(s, actor_id, conversation_id, True)

    def delete(self, actor_id, conversation_id):
        with self.factory.begin() as s:
            row = self._owned(s, actor_id, conversation_id, True)
            if row["active_generation_id"]:
                raise ApplicationError("CONVERSATION_BUSY", "请先停止当前回复，再删除讨论", True)
            s.execute(delete(sessions).where(sessions.c.id == conversation_id))

    def messages(self, actor_id, conversation_id, after_seq, limit):
        with self.factory.begin() as s:
            self._owned(s, actor_id, conversation_id, True)
            rows = list(
                s.execute(
                    select(messages)
                    .where(messages.c.session_id == conversation_id, messages.c.seq > after_seq)
                    .order_by(messages.c.seq)
                    .limit(limit + 1)
                ).mappings()
            )
            return {
                "messages": [self.public_message(r) for r in rows[:limit]],
                "next_after_seq": rows[limit - 1]["seq"] if len(rows) > limit else None,
            }

    @staticmethod
    def public_message(row):
        return {k: row[k] for k in ("id", "seq", "role", "status", "content", "created_at")}

    def prepare(self, actor_id, conversation_id, client_id, content, daily_limit, global_limit):
        with self.factory.begin() as s:
            s.execute(text("SELECT pg_advisory_xact_lock(913027)"))
            session = self._owned(s, actor_id, conversation_id, True)
            if session["status"] != "active":
                raise ApplicationError("INVALID_INPUT", "讨论已结束或过期，请重新开始")
            prior = (
                s.execute(
                    select(messages).where(
                        messages.c.session_id == conversation_id,
                        messages.c.client_message_id == client_id,
                    )
                )
                .mappings()
                .first()
            )
            if prior and prior["content"] != content:
                raise ApplicationError("IDEMPOTENCY_CONFLICT", "同一消息标识不能用于不同内容")
            assistant = None
            if prior:
                assistant = (
                    s.execute(
                        select(messages).where(
                            messages.c.session_id == conversation_id,
                            messages.c.seq == prior["seq"] + 1,
                        )
                    )
                    .mappings()
                    .one()
                )
                if assistant["status"] == "completed":
                    return {
                        "actor_id": actor_id,
                        "session_id": conversation_id,
                        "message_id": assistant["id"],
                        "seq": assistant["seq"],
                        "replay": assistant["content"],
                        "generation_id": None,
                    }
            if session["active_generation_id"]:
                raise ApplicationError("CONVERSATION_BUSY", "上一条回复仍在生成，请稍候", True)
            if assistant and assistant["seq"] != session["last_message_seq"]:
                raise ApplicationError(
                    "IDEMPOTENCY_CONFLICT", "这条旧消息不能重新生成，请发送新消息"
                )
            now = datetime.now(UTC)
            day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            count = (
                select(func.count())
                .select_from(messages.join(sessions, messages.c.session_id == sessions.c.id))
                .where(messages.c.role == "assistant", messages.c.created_at >= day)
            )
            if (
                s.scalar(count) >= global_limit
                or s.scalar(count.where(sessions.c.actor_id == actor_id)) >= daily_limit
            ):
                raise ApplicationError("RATE_LIMITED", "今日讨论次数已达上限，请明天再来", True)
            generation_id = uuid4()
            seq = assistant["seq"] if assistant else session["last_message_seq"] + 2
            message_id = assistant["id"] if assistant else uuid4()
            if not prior:
                s.execute(
                    insert(messages).values(
                        session_id=conversation_id,
                        seq=seq - 1,
                        role="user",
                        status="completed",
                        client_message_id=client_id,
                        content=content,
                    )
                )
                s.execute(
                    insert(messages).values(
                        id=message_id,
                        session_id=conversation_id,
                        seq=seq,
                        role="assistant",
                        status="generating",
                    )
                )
            else:
                s.execute(
                    update(messages)
                    .where(messages.c.id == message_id)
                    .values(status="generating", content="", created_at=now, completed_at=None)
                )
            s.execute(
                update(sessions)
                .where(sessions.c.id == conversation_id)
                .values(last_message_seq=seq, active_generation_id=generation_id, updated_at=now)
            )
            return {
                "actor_id": actor_id,
                "session_id": conversation_id,
                "message_id": message_id,
                "seq": seq,
                "generation_id": generation_id,
                "content": content,
            }

    def finish(self, turn, content, status, model):
        with self.factory.begin() as s:
            row = s.execute(
                select(sessions)
                .where(
                    sessions.c.id == turn["session_id"],
                    sessions.c.active_generation_id == turn["generation_id"],
                )
                .with_for_update()
            ).first()
            if not row:
                return False
            s.execute(
                update(messages)
                .where(messages.c.id == turn["message_id"])
                .values(
                    content=content if status == "completed" else "",
                    status=status,
                    model_name=model,
                    completed_at=datetime.now(UTC),
                )
            )
            s.execute(
                update(sessions)
                .where(sessions.c.id == turn["session_id"])
                .values(active_generation_id=None, updated_at=datetime.now(UTC))
            )
            return True

    def history(self, actor_id, conversation_id, before_seq):
        with self.factory() as s:
            self._owned(s, actor_id, conversation_id)
            summary = (
                s.execute(
                    select(summaries)
                    .where(summaries.c.session_id == conversation_id)
                    .order_by(summaries.c.covered_until_seq.desc())
                    .limit(1)
                )
                .mappings()
                .first()
            )
            covered = summary["covered_until_seq"] if summary else 0
            rows = list(
                s.execute(
                    select(messages)
                    .where(
                        messages.c.session_id == conversation_id,
                        messages.c.seq > covered,
                        messages.c.seq < before_seq,
                    )
                    .order_by(messages.c.seq)
                ).mappings()
            )
            complete = []
            for i in range(len(rows) - 1):
                a, b = rows[i], rows[i + 1]
                if a["role"] == "user" and b["role"] == "assistant" and b["status"] == "completed":
                    complete.extend([dict(a), dict(b)])
            return dict(summary) if summary else None, complete

    def save_summary(self, turn, covered_seq, value):
        with self.factory.begin() as s:
            self._owned(s, turn["actor_id"], turn["session_id"], True)
            latest = (
                s.scalar(
                    select(func.max(summaries.c.version)).where(
                        summaries.c.session_id == turn["session_id"]
                    )
                )
                or 0
            )
            s.execute(
                pg_insert(summaries)
                .values(
                    session_id=turn["session_id"],
                    version=latest + 1,
                    covered_until_seq=covered_seq,
                    summary_json=value,
                )
                .on_conflict_do_nothing()
            )
