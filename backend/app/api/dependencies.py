from app.modules.identity.application.service import IdentityService
from app.shared.health import HealthService
from fastapi import Request


def identity_service(request: Request) -> IdentityService:
    return request.app.state.services.identity


def health_service(request: Request) -> HealthService:
    return request.app.state.services.health
