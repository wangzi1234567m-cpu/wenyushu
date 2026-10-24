from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class StrictDto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionCreated(StrictDto):
    expires_at: datetime
    csrf_token: str


class HealthStatus(StrictDto):
    status: Literal["ok", "degraded"]


class Ok(StrictDto):
    ok: Literal[True]


class Error(StrictDto):
    code: str
    message: str
    retryable: bool
    request_id: str


class ErrorEnvelope(StrictDto):
    error: Error


ERROR_RESPONSES = {
    code: {"model": ErrorEnvelope, "description": "失败时遵循统一错误契约"}
    for code in (400, 401, 403, 409, 422, 429, 500, 503)
}
