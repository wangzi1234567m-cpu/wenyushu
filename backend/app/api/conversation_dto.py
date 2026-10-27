from datetime import datetime
from typing import Literal
from uuid import UUID

from app.api.dto import StrictDto
from pydantic import Field


class ConversationCreate(StrictDto):
    kind: Literal["discussion"]
    topic_id: UUID | None
    exploration_id: UUID | None = None


class Conversation(StrictDto):
    conversation_id: UUID
    kind: Literal["discussion"]
    topic_id: UUID | None
    status: Literal["active", "closed", "expired"]
    last_message_seq: int = Field(ge=0)
    created_at: datetime
    provider_mode: Literal["mock", "deepseek"] = "mock"


class ConversationMessage(StrictDto):
    id: UUID
    seq: int = Field(ge=1)
    role: Literal["user", "assistant"]
    status: Literal["pending", "generating", "completed", "failed", "blocked"]
    content: str
    created_at: datetime


class ConversationMessagePage(StrictDto):
    messages: list[ConversationMessage]
    next_after_seq: int | None = Field(ge=0)


class ConversationMessageCreate(StrictDto):
    client_message_id: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=4000)
