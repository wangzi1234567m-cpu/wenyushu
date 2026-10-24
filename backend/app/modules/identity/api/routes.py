from typing import Annotated

from app.api.dependencies import identity_service
from app.api.dto import ERROR_RESPONSES, Ok, SessionCreated
from app.modules.identity.application.service import IdentityService
from fastapi import APIRouter, Depends, Header, Response
from fastapi.security import APIKeyCookie

router = APIRouter(tags=["Auth"], responses=ERROR_RESPONSES)
cookie = APIKeyCookie(name="wqs_session", scheme_name="ActorCookieAuth", auto_error=False)
Service = Annotated[IdentityService, Depends(identity_service)]
Credential = Annotated[str | None, Depends(cookie)]


@router.post(
    "/auth/anonymous-session",
    status_code=201,
    response_model=SessionCreated,
    operation_id="createAnonymousSession",
)
def bootstrap(response: Response, service: Service, credential: Credential):
    result = service.bootstrap(credential)
    response.set_cookie(
        "wqs_session",
        result.credential,
        expires=result.expires_at,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return SessionCreated(expires_at=result.expires_at, csrf_token=result.csrf_token)


@router.delete("/auth/anonymous-session", response_model=Ok, operation_id="revokeAnonymousSession")
def revoke(
    response: Response,
    service: Service,
    credential: Credential,
    csrf_token: Annotated[str, Header(alias="X-CSRF-Token")],
):
    service.revoke(credential, csrf_token)
    response.delete_cookie("wqs_session", path="/", secure=True, httponly=True, samesite="lax")
    return Ok(ok=True)
