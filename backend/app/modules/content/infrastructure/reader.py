import logging
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.modules.content.application.ports import validated_flow
from app.modules.content.infrastructure.models import (
    daily_schedules_table as schedules,
)
from app.modules.content.infrastructure.models import (
    question_versions_table as versions,
)
from app.modules.content.infrastructure.models import (
    questions_table as questions,
)
from app.modules.content.infrastructure.models import (
    topics_table as topics,
)
from app.shared.errors import ApplicationError


class SqlContentReader:
    def __init__(self, factory):
        self.factory = factory

    def topics(self, limit):
        with self.factory() as session:
            return [
                dict(r)
                for r in session.execute(
                    select(topics.c.id, topics.c.slug, topics.c.title, topics.c.audience)
                    .where(topics.c.status == "published", topics.c.audience == "adult")
                    .order_by(topics.c.slug)
                    .limit(limit)
                ).mappings()
            ]

    def version(self, version_id, allow_retired=False):
        with self.factory() as session:
            row = (
                session.execute(select(versions).where(versions.c.id == version_id))
                .mappings()
                .first()
            )
            if row is None or (
                not allow_retired and (row["status"] != "published" or row["audience"] != "adult")
            ):
                raise ApplicationError("NOT_FOUND", "题目暂不可用")
            result = dict(row)
            question = (
                session.execute(select(questions).where(questions.c.id == row["question_id"]))
                .mappings()
                .one()
            )
            topic = (
                session.execute(select(topics).where(topics.c.id == question["topic_id"]))
                .mappings()
                .one()
            )
            if not allow_retired and (
                topic["status"] != "published" or topic["audience"] != "adult"
            ):
                raise ApplicationError("NOT_FOUND", "题目暂不可用")
            result["topic"] = {k: topic[k] for k in ("id", "slug", "title", "audience")}
            validated_flow(result)
            return result

    def daily(self, now):
        date = now.astimezone(ZoneInfo("Asia/Shanghai")).date()
        with self.factory() as session:
            scheduled = session.scalar(
                select(schedules.c.question_version_id).where(
                    schedules.c.local_date == date,
                    schedules.c.audience == "adult",
                    schedules.c.status == "published",
                )
            )
            candidates = ([scheduled] if scheduled else []) + list(
                session.scalars(
                    select(versions.c.id)
                    .where(
                        versions.c.status == "published",
                        versions.c.flow_json["fallback"].as_boolean().is_(True),
                    )  # noqa: E712
                    .order_by(versions.c.created_at, versions.c.id)
                )
            )
        for index, version_id in enumerate(candidates):
            try:
                version = self.version(version_id)
                if not scheduled or index:
                    logging.getLogger("wqs.content").warning(
                        "daily schedule unavailable; reviewed fallback"
                    )
                return {
                    "question_id": version["question_id"],
                    "question_version_id": version["id"],
                    "local_date": date,
                    "timezone": "Asia/Shanghai",
                    "title": version["title"],
                    "intro": version["intro"],
                    "topic": version["topic"],
                    "first_step": validated_flow(version).public_step(
                        validated_flow(version).first_step_id
                    ),
                }
            except ApplicationError:
                continue
        raise ApplicationError("SERVICE_UNAVAILABLE", "今日问题暂不可用，请稍后再试", True)
