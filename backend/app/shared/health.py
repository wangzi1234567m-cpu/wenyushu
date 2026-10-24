from collections.abc import Callable

from app.shared.errors import ApplicationError


class HealthService:
    def __init__(self, probe: Callable[[], bool]):
        self.probe = probe

    def ready(self) -> None:
        if not self.probe():
            raise ApplicationError("SERVICE_UNAVAILABLE", "服务暂未就绪", True)
