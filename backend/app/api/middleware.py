import logging
import time
from uuid import uuid4

from app.api.errors import error_response
from starlette.datastructures import Headers, MutableHeaders

logger = logging.getLogger("wqs.request")


class RequestGuard:
    """Bound the actual stream, including bodies without Content-Length."""

    def __init__(self, app, allowed_origins: list[str], max_body_bytes: int):
        self.app = app
        self.origins = frozenset(allowed_origins)
        self.limit = max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = False
        status = 500
        start = time.monotonic()

        async def safe_send(message):
            nonlocal started, status
            if message["type"] == "http.response.start":
                started = True
                status = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["Cache-Control"] = "no-store"
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "no-referrer"
            await send(message)

        async def reject(code, message, http_status=422):
            await error_response(request_id, http_status, code, message)(scope, receive, safe_send)

        try:
            headers = Headers(scope=scope)
            if scope["method"] not in ("GET", "HEAD", "OPTIONS"):
                if headers.get("origin") not in self.origins:
                    return await reject("ORIGIN_REJECTED", "请求来源不被允许", 403)
            length = headers.get("content-length")
            if length is not None:
                try:
                    if int(length) < 0 or int(length) > self.limit:
                        return await reject("INVALID_INPUT", "请求体超过限制")
                except ValueError:
                    return await reject("INVALID_INPUT", "请求长度不合法")
            messages = []
            size = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                size += len(message.get("body", b""))
                if size > self.limit:
                    return await reject("INVALID_INPUT", "请求体超过限制")
                messages.append(message)
                if not message.get("more_body", False):
                    break
            iterator = iter(messages)

            async def replay():
                return next(iterator, {"type": "http.request", "body": b"", "more_body": False})

            await self.app(scope, replay, safe_send)
        except Exception:
            if not started:
                await reject("SERVICE_INTERNAL_ERROR", "服务暂时不可用", 500)
        finally:
            route = scope.get("route")
            # Never log a raw path/query, which may contain user content.
            logger.info(
                "request_id=%s route=%s status=%s duration_ms=%.1f",
                request_id,
                getattr(route, "path", "unmatched"),
                status,
                (time.monotonic() - start) * 1000,
            )
