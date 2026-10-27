from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReadingPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    genre: str | None = None
    style: list[str] = Field(default_factory=list)
    difficulty: str | None = None
    language: str = "zh-CN"


class DailyReadingIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor_id: UUID
    source_ref_id: UUID
    central_question: str = Field(max_length=1200)
    topics: list[str] = Field(max_length=10)
    focus: str = Field(max_length=1200)
    preferences: ReadingPreferences
    schema_version: int = 1


class ReadingIntentCommand(Protocol):
    def create_daily(self, intent: DailyReadingIntent) -> UUID: ...


class ReadingRepository(Protocol):
    def create_daily(self, intent: DailyReadingIntent) -> UUID: ...
    def intent(self, actor_id: UUID, intent_id: UUID) -> dict: ...
    def create_job(self, actor_id: UUID, intent_id: UUID, key: str, limit: int) -> dict: ...
    def job(self, actor_id: UUID, job_id: UUID) -> dict: ...
    def finish_job(self, job_id: UUID, items: list[dict], limit: int) -> dict: ...


class RecommendationPort(Protocol):
    def recommend(self, intent: dict, limit: int) -> list[dict]: ...
