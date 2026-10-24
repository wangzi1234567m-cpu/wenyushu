from typing import Annotated

from app.api.dependencies import health_service
from app.api.dto import ERROR_RESPONSES, HealthStatus
from app.modules.identity.api.routes import router as identity_router
from app.shared.health import HealthService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1")
router.include_router(identity_router)


@router.get(
    "/health/live",
    response_model=HealthStatus,
    operation_id="healthLive",
    tags=["Health"],
    responses=ERROR_RESPONSES,
)
def live():
    return HealthStatus(status="ok")


@router.get(
    "/health/ready",
    response_model=HealthStatus,
    operation_id="healthReady",
    tags=["Health"],
    responses=ERROR_RESPONSES,
)
def ready(service: Annotated[HealthService, Depends(health_service)]):
    service.ready()
    return HealthStatus(status="ok")
