from app.shared.errors import ApplicationError
from fastapi import Request
from starlette.responses import JSONResponse

STATUS = {
    "UNAUTHORIZED": 401,
    "NOT_FOUND": 404,
    "CSRF_REJECTED": 403,
    "ORIGIN_REJECTED": 403,
    "INVALID_INPUT": 422,
    "SERVICE_UNAVAILABLE": 503,
    "INVALID_EXPLORATION_STEP": 409,
    "IDEMPOTENCY_CONFLICT": 409,
    "CONTENT_BLOCKED": 422,
}


def error_response(
    request_id: str, status: int, code: str, message: str, retryable: bool = False
) -> JSONResponse:
    return JSONResponse(
        {
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "request_id": request_id,
            }
        },
        status_code=status,
    )


async def application_error(request: Request, error: ApplicationError):
    return error_response(
        request.state.request_id,
        STATUS.get(error.code, 500),
        error.code,
        error.message,
        error.retryable,
    )


async def validation_error(request: Request, error: Exception):
    return error_response(request.state.request_id, 422, "INVALID_INPUT", "请求参数不合法")


async def http_error(request: Request, error):
    return error_response(
        request.state.request_id,
        error.status_code,
        "NOT_FOUND" if error.status_code == 404 else "INVALID_INPUT",
        "资源不存在" if error.status_code == 404 else "请求不被允许",
    )
