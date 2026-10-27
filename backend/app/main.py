import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from app.api.errors import application_error, http_error, validation_error
from app.api.middleware import RequestGuard
from app.api.v1.routes import router
from app.bootstrap.container import Services, build_services
from app.infrastructure.settings.config import Settings
from app.shared.errors import ApplicationError


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = settings or Settings()
    engine = None
    if services is None:
        services, engine = build_services(settings)

    @asynccontextmanager
    async def lifespan(app):
        yield
        if engine is not None:
            engine.dispose()

    app = FastAPI(
        title="问与书 Web MVP API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    app.state.services = services
    app.include_router(router)
    app.add_exception_handler(ApplicationError, application_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_middleware(
        RequestGuard,
        allowed_origins=settings.allowed_origins,
        max_body_bytes=settings.max_body_bytes,
    )
    # Bootstrap accepts an optional cookie, but does not require authentication.
    original_openapi = app.openapi

    def openapi():
        schema = original_openapi()
        schema["paths"]["/api/v1/auth/anonymous-session"]["post"].pop("security", None)
        return schema

    app.openapi = openapi
    return app
