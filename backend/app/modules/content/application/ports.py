from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.content.domain.flow import QuestionFlow


class DailyQuestionReader(Protocol):
    def daily(self, now: datetime) -> dict: ...
    def version(self, version_id: UUID, allow_retired: bool = False) -> dict: ...
    def topics(self, limit: int) -> list[dict]: ...


def validated_flow(version: dict) -> QuestionFlow:
    return QuestionFlow.model_validate(version["flow_json"])
