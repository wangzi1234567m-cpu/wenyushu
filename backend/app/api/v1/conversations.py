from typing import Annotated
from uuid import UUID

from app.api.conversation_dto import (
    Conversation,
    ConversationCreate,
    ConversationMessageCreate,
    ConversationMessagePage,
)
from app.api.dto import ERROR_RESPONSES, Ok
from app.api.v1.daily import Actor, Writer
from fastapi import APIRouter, Query, Request
from starlette.responses import StreamingResponse

router = APIRouter(responses=ERROR_RESPONSES, tags=["Conversation"])


def public(row, services):
    return {
        "conversation_id": row["id"],
        **{k: row[k] for k in ("kind", "topic_id", "status", "last_message_seq", "created_at")},
        "provider_mode": services.provider_mode,
    }


@router.post(
    "/conversations",
    operation_id="createConversation",
    status_code=201,
    response_model=Conversation,
)
def create(body: ConversationCreate, request: Request, current: Writer):
    services = request.app.state.services
    return public(
        services.discussion.create(current.id, body.topic_id, body.exploration_id), services
    )


@router.get(
    "/conversations/{conversation_id}", operation_id="getConversation", response_model=Conversation
)
def get(conversation_id: UUID, request: Request, current: Actor):
    services = request.app.state.services
    return public(services.conversations.get(current.id, conversation_id), services)


@router.delete(
    "/conversations/{conversation_id}", operation_id="deleteConversation", response_model=Ok
)
def delete(conversation_id: UUID, request: Request, current: Writer):
    request.app.state.services.discussion.delete(current.id, conversation_id)
    return {"ok": True}


@router.get(
    "/conversations/{conversation_id}/messages",
    operation_id="listConversationMessages",
    response_model=ConversationMessagePage,
)
def history(
    conversation_id: UUID,
    request: Request,
    current: Actor,
    after_seq: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
):
    return request.app.state.services.conversations.messages(
        current.id, conversation_id, after_seq, limit
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    operation_id="sendConversationMessage",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
async def send(
    conversation_id: UUID, body: ConversationMessageCreate, request: Request, current: Writer
):
    runtime = request.app.state.services.runtime
    turn = await runtime.prepare(current.id, conversation_id, body.client_message_id, body.content)
    return StreamingResponse(
        runtime.stream(turn, request.state.request_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
