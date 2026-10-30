from datetime import datetime
from typing import Literal
from uuid import UUID

from app.api.dto import StrictDto
from pydantic import Field, model_validator


class ViewpointExtractionCreate(StrictDto):
    up_to_seq: int = Field(ge=1)


class ViewpointCandidate(StrictDto):
    viewpoint_id: UUID
    content: str = Field(min_length=12, max_length=240)
    source_message_ids: list[UUID] = Field(min_length=1, max_length=4)


class ViewpointExtraction(StrictDto):
    extraction_id: UUID | None
    up_to_seq: int = Field(ge=0)
    status: Literal["not_requested", "processing", "succeeded", "failed"]
    items: list[ViewpointCandidate] = Field(max_length=3)


class SavedViewpointCreate(StrictDto):
    conversation_id: UUID
    message_id: UUID | None = None
    extraction_id: UUID | None = None
    item_index: int | None = Field(default=None, ge=0, le=2)

    @model_validator(mode="after")
    def one_source(self):
        if self.message_id:
            if self.extraction_id is not None or self.item_index is not None:
                raise ValueError("Choose one source")
        elif self.extraction_id is None or self.item_index is None:
            raise ValueError("Source required")
        return self


class SavedViewpoint(StrictDto):
    id: UUID
    conversation_id: UUID
    message_id: UUID | None
    source_message_ids: list[UUID] = Field(min_length=1, max_length=4)
    source_type: Literal["user_quote", "ai_viewpoint", "ai_summary"]
    content: str = Field(min_length=1, max_length=16000)
    topic_title: str = Field(max_length=300)
    created_at: datetime
    source_available: bool


class SavedViewpointPage(StrictDto):
    items: list[SavedViewpoint]
    next_offset: int | None = Field(ge=0)
