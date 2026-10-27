from datetime import timedelta

from sqlalchemy import insert, select, update

from app.modules.content.application.ports import validated_flow
from app.modules.exploration.infrastructure.models import exploration_answers_table as answers
from app.modules.exploration.infrastructure.models import explorations_table as explorations
from app.shared.errors import ApplicationError


class SqlExplorationRepository:
    def __init__(self, factory):
        self.factory = factory

    def owned_version(self, actor_id, version_id):
        with self.factory() as s:
            return (
                s.scalar(
                    select(explorations.c.id)
                    .where(
                        explorations.c.actor_id == actor_id,
                        explorations.c.question_version_id == version_id,
                    )
                    .limit(1)
                )
                is not None
            )

    def _load(self, s, actor_id, exploration_id, now, lock=False):
        query = select(explorations).where(
            explorations.c.id == exploration_id, explorations.c.actor_id == actor_id
        )
        if lock:
            query = query.with_for_update()
        row = s.execute(query).mappings().first()
        if row is None:
            raise ApplicationError("NOT_FOUND", "资源不存在")
        state = dict(row)
        if state["status"] == "active" and now >= state["expires_at"]:
            s.execute(
                update(explorations)
                .where(explorations.c.id == exploration_id)
                .values(status="expired")
            )
            state["status"] = "expired"
        state["answers"] = [
            dict(r)
            for r in s.execute(
                select(
                    answers.c.step_id,
                    answers.c.option_id,
                    answers.c.option_ids,
                    answers.c.supplementary_text,
                )
                .where(answers.c.exploration_id == exploration_id)
                .order_by(answers.c.submitted_at, answers.c.id)
            ).mappings()
        ]
        return state

    def create(self, actor_id, version, now):
        with self.factory.begin() as s:
            key = s.scalar(
                insert(explorations)
                .values(
                    actor_id=actor_id,
                    question_version_id=version["id"],
                    current_step_id=validated_flow(version).first_step_id,
                    created_at=now,
                    updated_at=now,
                    expires_at=now + timedelta(days=7),
                )
                .returning(explorations.c.id)
            )
            return self._load(s, actor_id, key, now)

    def get(self, actor_id, exploration_id, now):
        with self.factory.begin() as s:
            return self._load(s, actor_id, exploration_id, now, True)

    def submit(self, actor_id, exploration_id, answer, version, now):
        answer = {"option_ids": None, **answer}
        with self.factory.begin() as s:
            state = self._load(s, actor_id, exploration_id, now, True)
            if state["status"] == "expired":
                raise ApplicationError("INVALID_EXPLORATION_STEP", "探索已过期，请重新开始")
            previous = next(
                (a for a in state["answers"] if a["step_id"] == answer["step_id"]), None
            )
            if previous:
                if previous != answer:
                    raise ApplicationError("IDEMPOTENCY_CONFLICT", "修改答案需要创建新的探索")
                return state
            if state["status"] != "active" or state["current_step_id"] != answer["step_id"]:
                raise ApplicationError("INVALID_EXPLORATION_STEP", "请按当前步骤作答")
            step = validated_flow(version).steps[answer["step_id"]]
            option = next((o for o in step.options if o.id == answer["option_id"]), None)
            if option is None:
                raise ApplicationError("INVALID_EXPLORATION_STEP", "选项不属于当前步骤")
            ids = answer.get("option_ids") or [answer["option_id"]]
            if (not step.multiple and len(ids) > 1) or any(
                key not in {o.id for o in step.options} for key in ids
            ):
                raise ApplicationError("INVALID_EXPLORATION_STEP", "选项不属于当前步骤")
            if "other" in ids and not answer.get("supplementary_text"):
                raise ApplicationError("INVALID_INPUT", "选择其他时，请补充你的想法")
            s.execute(insert(answers).values(exploration_id=exploration_id, **answer))
            s.execute(
                update(explorations)
                .where(explorations.c.id == exploration_id)
                .values(current_step_id=option.next_step_id, updated_at=now)
            )
            return self._load(s, actor_id, exploration_id, now)

    def link_intent(self, actor_id, exploration_id, intent_id):
        with self.factory.begin() as s:
            s.execute(
                update(explorations)
                .where(
                    explorations.c.id == exploration_id,
                    explorations.c.actor_id == actor_id,
                    explorations.c.current_step_id.is_(None),
                    explorations.c.status == "active",
                )
                .values(status="completed", reading_intent_id=intent_id)
            )
