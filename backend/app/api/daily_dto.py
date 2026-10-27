"""P1 HTTP DTOs. Keep in sync with contracts/openapi.yaml."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from app.api.dto import StrictDto
from pydantic import Field, field_validator, model_validator


class Topic(StrictDto):
    id: UUID
    slug: str
    title: str
    description: str = Field(default=None)
    audience: Literal["adult", "teen", "child", "all"]


class Option(StrictDto):
    id: str
    label: str
    description: str = Field(default=None)


class QuestionStep(StrictDto):
    id: str
    prompt: str
    options: list[Option]
    optional: bool
    multiple: bool = False
    source_url: str = Field(default=None)


class DailyQuestion(StrictDto):
    question_id: UUID
    question_version_id: UUID
    local_date: date
    timezone: str
    title: str
    intro: str
    topic: Topic
    first_step: QuestionStep


class ExplorationCreate(StrictDto):
    question_version_id: UUID


class ExplorationAnswer(StrictDto):
    step_id: str
    option_id: str
    option_ids: list[str] | None = Field(default=None, min_length=1, max_length=6)
    supplementary_text: Annotated[str, Field(max_length=300)] | None = None

    @field_validator("supplementary_text", mode="before")
    @classmethod
    def normalize_text(cls, value):
        if isinstance(value, str):
            if len(value) > 300:
                raise ValueError("Supplement exceeds 300 characters")
            return value.strip() or None
        return value

    @model_validator(mode="after")
    def normalize_selection(self):
        if self.option_ids is not None:
            if (
                len(set(self.option_ids)) != len(self.option_ids)
                or self.option_id not in self.option_ids
            ):
                raise ValueError("Invalid multiple selection")
            self.option_ids = sorted(self.option_ids)
            self.option_id = self.option_ids[0]
        return self


class ExplorationAnswerRecord(ExplorationAnswer):
    step_prompt: str = Field(default=None)
    option_label: str = Field(default=None)


class ExplorationState(StrictDto):
    exploration_id: UUID
    question_version_id: UUID
    status: Literal["active", "completed", "expired"]
    next_step: QuestionStep | None
    reading_intent_id: UUID | None
    answers: list[ExplorationAnswerRecord] = Field(default=None, max_length=3)


class RecommendationCreate(StrictDto):
    reading_intent_id: UUID
    limit: int = Field(default=3, ge=1, le=3)


class VerifiedBook(StrictDto):
    work_id: UUID
    title: str
    author: str
    summary: str
    recommendation_reason: str
    rank: int = Field(ge=1, le=3)
    verification_status: Literal["verified"]
    evidence_urls: list[Annotated[str, Field(json_schema_extra={"format": "uri"})]]


class TaskError(StrictDto):
    code: str
    message: str
    retryable: bool


class RecommendationJob(StrictDto):
    job_id: UUID
    status: Literal["pending", "processing", "succeeded", "partial", "failed"]
    items: list[VerifiedBook] = Field(max_length=3)
    error: TaskError | None
    created_at: datetime
    completed_at: datetime | None


Topic.model_rebuild()

Option.model_rebuild()

QuestionStep.model_rebuild()

DailyQuestion.model_rebuild()

ExplorationCreate.model_rebuild()

ExplorationAnswer.model_rebuild()

ExplorationState.model_rebuild()

RecommendationCreate.model_rebuild()

VerifiedBook.model_rebuild()

TaskError.model_rebuild()

RecommendationJob.model_rebuild()
