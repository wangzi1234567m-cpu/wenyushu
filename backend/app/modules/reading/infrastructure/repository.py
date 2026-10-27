import hashlib
from datetime import UTC, datetime

from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.modules.reading.infrastructure.models import intents_table as intents
from app.modules.reading.infrastructure.models import recommendation_items_table as items
from app.modules.reading.infrastructure.models import recommendation_jobs_table as jobs
from app.shared.errors import ApplicationError


class SqlReadingRepository:
    def __init__(self, factory):
        self.factory = factory

    def create_daily(self, intent):
        data = intent.model_dump(mode="python")
        data["preferences"] = intent.preferences.model_dump()
        data.update(source_type="daily_question", purpose="exploration")
        with self.factory.begin() as s:
            s.execute(pg_insert(intents).values(**data).on_conflict_do_nothing())
            return s.scalar(
                select(intents.c.id).where(
                    intents.c.actor_id == intent.actor_id,
                    intents.c.source_type == "daily_question",
                    intents.c.source_ref_id == intent.source_ref_id,
                )
            )

    def intent(self, actor_id, intent_id):
        with self.factory() as s:
            row = (
                s.execute(
                    select(intents).where(intents.c.id == intent_id, intents.c.actor_id == actor_id)
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ApplicationError("NOT_FOUND", "资源不存在")
            return dict(row)

    def create_job(self, actor_id, intent_id, key, limit):
        digest = hashlib.sha256(f"{intent_id}:{limit}".encode()).hexdigest()
        with self.factory.begin() as s:
            s.execute(
                pg_insert(jobs)
                .values(
                    actor_id=actor_id,
                    reading_intent_id=intent_id,
                    idempotency_key=key,
                    request_hash=digest,
                    requested_limit=limit,
                )
                .on_conflict_do_nothing()
            )
            row = (
                s.execute(
                    select(jobs).where(jobs.c.actor_id == actor_id, jobs.c.idempotency_key == key)
                )
                .mappings()
                .one()
            )
            if row["request_hash"] != digest:
                raise ApplicationError("IDEMPOTENCY_CONFLICT", "相同请求标识对应不同参数")
            return self._job(s, row)

    def _job(self, s, row):
        return {
            "job_id": row["id"],
            "status": row["status"],
            "items": [
                dict(r)
                for r in s.execute(
                    select(
                        items.c.work_id,
                        items.c.title,
                        items.c.author,
                        items.c.summary,
                        items.c.recommendation_reason,
                        items.c.rank,
                        items.c.verification_status,
                        items.c.evidence_urls,
                    )
                    .where(items.c.job_id == row["id"])
                    .order_by(items.c.rank)
                ).mappings()
            ],
            "error": {
                "code": row["error_code"],
                "message": row["error_message"],
                "retryable": False,
            }
            if row["error_code"]
            else None,
            "created_at": row["created_at"],
            "completed_at": row["completed_at"],
        }

    def job(self, actor_id, job_id):
        with self.factory() as s:
            row = (
                s.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.actor_id == actor_id))
                .mappings()
                .first()
            )
            if row is None:
                raise ApplicationError("NOT_FOUND", "资源不存在")
            return self._job(s, row)

    def finish_job(self, job_id, result, limit):
        with self.factory.begin() as s:
            row = (
                s.execute(select(jobs).where(jobs.c.id == job_id).with_for_update())
                .mappings()
                .one()
            )
            if row["status"] != "pending":
                return self._job(s, row)
            for item in result:
                s.execute(insert(items).values(job_id=job_id, **item))
            status = ("succeeded" if len(result) == limit else "partial") if result else "failed"
            s.execute(
                update(jobs)
                .where(jobs.c.id == job_id)
                .values(
                    status=status,
                    completed_at=datetime.now(UTC),
                    error_code=None if result else "BOOK_VERIFICATION_FAILED",
                    error_message=None if result else "当前没有匹配的已核验样例，请调整选择",
                )
            )
            return self._job(s, s.execute(select(jobs).where(jobs.c.id == job_id)).mappings().one())
