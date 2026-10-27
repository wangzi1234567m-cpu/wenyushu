from typing import Annotated
from uuid import UUID

from app.api.daily_dto import (
    DailyQuestion,
    ExplorationAnswer,
    ExplorationCreate,
    ExplorationState,
    RecommendationCreate,
    RecommendationJob,
    Topic,
)
from app.api.dto import ERROR_RESPONSES
from app.modules.identity.api.routes import Credential, Service
from app.modules.identity.application.service import utcnow
from app.shared.errors import ApplicationError
from fastapi import APIRouter, Depends, Header, Query, Request

router = APIRouter(responses=ERROR_RESPONSES)


def actor(service: Service, credential: Credential):
    return service.resolve(credential)


def writing_actor(
    service: Service, credential: Credential, csrf: Annotated[str, Header(alias="X-CSRF-Token")]
):
    current = service.resolve(credential)
    if not service.csrf.verify(csrf, credential, service.clock()):
        raise ApplicationError("CSRF_REJECTED", "请求验证失败")
    return current


Actor = Annotated[object, Depends(actor)]
Writer = Annotated[object, Depends(writing_actor)]


@router.get(
    "/topics",
    operation_id="listTopics",
    response_model_exclude_unset=True,
    response_model=list[Topic],
)
def topics(request: Request, limit: Annotated[int, Query(ge=1, le=50)] = 20):
    return request.app.state.services.content.topics(limit)


@router.get(
    "/questions/daily",
    operation_id="getDailyQuestion",
    response_model_exclude_unset=True,
    response_model=DailyQuestion,
)
def daily(request: Request):
    return request.app.state.services.content.daily(utcnow())


@router.post(
    "/explorations",
    operation_id="createExploration",
    status_code=201,
    response_model_exclude_unset=True,
    response_model=ExplorationState,
)
def create_exploration(body: ExplorationCreate, request: Request, current: Writer):
    return request.app.state.services.exploration.create(current.id, body.question_version_id)


@router.get(
    "/explorations/{exploration_id}",
    operation_id="getExploration",
    response_model_exclude_unset=True,
    response_model=ExplorationState,
)
def get_exploration(exploration_id: UUID, request: Request, current: Actor):
    return request.app.state.services.exploration.get(current.id, exploration_id)


@router.post(
    "/explorations/{exploration_id}/answers",
    operation_id="answerExploration",
    response_model_exclude_unset=True,
    response_model=ExplorationState,
)
def answer_exploration(
    exploration_id: UUID, body: ExplorationAnswer, request: Request, current: Writer
):
    return request.app.state.services.exploration.answer(
        current.id, exploration_id, body.model_dump()
    )


@router.post(
    "/recommendations",
    operation_id="createRecommendationJob",
    status_code=202,
    response_model_exclude_unset=True,
    response_model=RecommendationJob,
)
def create_recommendation(
    body: RecommendationCreate,
    request: Request,
    current: Writer,
    key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
):
    return request.app.state.services.reading.create_recommendation(
        current.id, body.reading_intent_id, key, body.limit
    )


@router.get(
    "/recommendations/{job_id}",
    operation_id="getRecommendationJob",
    response_model_exclude_unset=True,
    response_model=RecommendationJob,
)
def recommendation(job_id: UUID, request: Request, current: Actor):
    return request.app.state.services.reading.job(current.id, job_id)
