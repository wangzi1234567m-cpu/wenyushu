from collections.abc import AsyncIterator
from typing import Literal

from app.integrations.llm.ports import ChatMessage, GenerationConfig, T
from app.shared.errors import ApplicationError


class MockLLM:
    def __init__(
        self,
        payload: dict | None = None,
        chunks: tuple[str, ...] = ("Mock",),
        mode: Literal["ok", "error", "timeout"] = "ok",
    ):
        self.payload = payload if payload is not None else {}
        self.chunks = chunks
        self.mode = mode

    def _check(self):
        if self.mode == "timeout":
            raise TimeoutError("Mock provider timeout")
        if self.mode == "error":
            raise ApplicationError("MODEL_UNAVAILABLE", "模型暂时不可用", True)

    async def generate_structured(
        self, schema: type[T], messages: list[ChatMessage], config: GenerationConfig
    ) -> T:
        self._check()
        return schema.model_validate(self.payload, strict=True)

    async def stream_chat(
        self, messages: list[ChatMessage], config: GenerationConfig
    ) -> AsyncIterator[str]:
        self._check()
        for chunk in self.chunks:
            yield chunk
