from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.modules.content.application.ports import DailyQuestionReader, validated_flow
from app.modules.exploration.application.ports import ExplorationRepository
from app.modules.identity.application.service import utcnow
from app.modules.reading.application.ports import (
    DailyReadingIntent,
    ReadingIntentCommand,
    ReadingPreferences,
)
from app.modules.safety.application.ports import SafetyPort


class ExplorationService:
    def __init__(
        self,
        repository: ExplorationRepository,
        content: DailyQuestionReader,
        reading: ReadingIntentCommand,
        safety: SafetyPort,
        clock: Callable[[], datetime] = utcnow,
    ):
        self.repo, self.content, self.reading, self.safety, self.clock = (
            repository,
            content,
            reading,
            safety,
            clock,
        )

    def create(self, actor_id: UUID, version_id: UUID):
        version = self.content.version(version_id, self.repo.owned_version(actor_id, version_id))
        return self._response(self.repo.create(actor_id, version, self.clock()), version)

    def get(self, actor_id: UUID, exploration_id: UUID):
        state = self.repo.get(actor_id, exploration_id, self.clock())
        return self._response(state, self.content.version(state["question_version_id"], True))

    def answer(self, actor_id: UUID, exploration_id: UUID, answer: dict):
        self.safety.check_supplement(answer.get("supplementary_text"))
        before = self.repo.get(actor_id, exploration_id, self.clock())
        version = self.content.version(before["question_version_id"], True)
        state = self.repo.submit(actor_id, exploration_id, answer, version, self.clock())
        if (
            state["status"] != "expired"
            and state["current_step_id"] is None
            and not state["reading_intent_id"]
        ):
            flow = validated_flow(version)
            topics, focus, style = [], [], []
            genre = None
            for item in self._ordered_answers(state, version):
                selected = item.get("option_ids") or [item["option_id"]]
                for option in flow.steps[item["step_id"]].options:
                    if option.id in selected:
                        topics.extend(option.topics)
                        if option.focus:
                            focus.append(option.focus)
                        genre = option.genre or genre
                        style.extend(option.style)
                if item.get("supplementary_text"):
                    focus.append(item["supplementary_text"])
            intent_id = self.reading.create_daily(
                DailyReadingIntent(
                    actor_id=actor_id,
                    source_ref_id=exploration_id,
                    central_question=version["title"],
                    topics=list(dict.fromkeys(topics))[:10],
                    focus="；".join(focus),
                    preferences=ReadingPreferences(genre=genre, style=list(dict.fromkeys(style))),
                )
            )
            self.repo.link_intent(actor_id, exploration_id, intent_id)
            state = self.repo.get(actor_id, exploration_id, self.clock())
        return self._response(state, version)

    def _response(self, state, version):
        return {
            "exploration_id": state["id"],
            "question_version_id": state["question_version_id"],
            "status": state["status"],
            "reading_intent_id": state["reading_intent_id"],
            "next_step": validated_flow(version).public_step(state["current_step_id"])
            if state["status"] == "active" and state["current_step_id"]
            else None,
            "answers": [
                {
                    **answer,
                    "step_prompt": validated_flow(version).steps[answer["step_id"]].prompt,
                    "option_label": "、".join(
                        o.label
                        for o in validated_flow(version).steps[answer["step_id"]].options
                        if o.id in (answer.get("option_ids") or [answer["option_id"]])
                    ),
                }
                for answer in self._ordered_answers(state, version)
            ],
        }

    def _ordered_answers(self, state, version):
        flow = validated_flow(version)
        by_step = {answer["step_id"]: answer for answer in state["answers"]}
        result, key = [], flow.first_step_id
        while key and key in by_step:
            answer = by_step[key]
            result.append(answer)
            key = next(
                o.next_step_id for o in flow.steps[key].options if o.id == answer["option_id"]
            )
        return result

    def discussion_seed(self, actor_id: UUID, exploration_id: UUID) -> dict:
        from app.shared.errors import ApplicationError

        state = self.repo.get(actor_id, exploration_id, self.clock())
        if state["status"] != "completed":
            raise ApplicationError("INVALID_EXPLORATION_STEP", "请先完成立场与理由的选择")
        version = self.content.version(state["question_version_id"], True)
        response = self._response(state, version)
        return {
            "question": version["title"],
            "question_version_id": str(version["id"]),
            "answers": [
                {
                    "question": a["step_prompt"],
                    "selection": a["option_label"],
                    "supplement": a.get("supplementary_text"),
                }
                for a in response["answers"]
            ],
        }
