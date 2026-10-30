from typing import Annotated
from uuid import UUID

from app.api.dto import ERROR_RESPONSES, Ok
from app.api.v1.daily import Actor, Writer
from app.api.viewpoint_dto import (
    SavedViewpoint,
    SavedViewpointCreate,
    SavedViewpointPage,
    ViewpointExtraction,
    ViewpointExtractionCreate,
)
from fastapi import APIRouter, Query, Request

router = APIRouter(responses=ERROR_RESPONSES, tags=["Discussion"])


@router.get(
    "/conversations/{conversation_id}/viewpoints",
    operation_id="getDiscussionViewpoints",
    response_model=ViewpointExtraction,
)
def cached(conversation_id: UUID, request: Request, current: Actor):
    return request.app.state.services.viewpoints.cached(current.id, conversation_id)


@router.post(
    "/conversations/{conversation_id}/viewpoints",
    operation_id="extractDiscussionViewpoints",
    response_model=ViewpointExtraction,
)
async def extract(
    conversation_id: UUID, body: ViewpointExtractionCreate, request: Request, current: Writer
):
    return await request.app.state.services.viewpoints.extract(
        current.id, conversation_id, body.up_to_seq
    )


@router.get(
    "/saved-viewpoints", operation_id="listSavedViewpoints", response_model=SavedViewpointPage
)
def listing(
    request: Request,
    current: Actor,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
    conversation_id: UUID | None = None,
):
    return request.app.state.services.viewpoints.list(current.id, limit, offset, conversation_id)


@router.post(
    "/saved-viewpoints",
    operation_id="saveViewpoint",
    status_code=201,
    response_model=SavedViewpoint,
)
def save(body: SavedViewpointCreate, request: Request, current: Writer):
    return request.app.state.services.viewpoints.save(
        current.id, body.conversation_id, body.message_id, body.extraction_id, body.item_index
    )


@router.delete(
    "/saved-viewpoints/{viewpoint_id}", operation_id="removeSavedViewpoint", response_model=Ok
)
def remove(viewpoint_id: UUID, request: Request, current: Writer):
    request.app.state.services.viewpoints.remove(current.id, viewpoint_id)
    return {"ok": True}
