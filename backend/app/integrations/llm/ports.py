from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class GenerationConfig:
    model: str = "mock"
    timeout_seconds: float = 10
    max_output_tokens: int = 512


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class LLMPort(Protocol):
    async def generate_structured(
        self, schema: type[T], messages: list[ChatMessage], config: GenerationConfig
    ) -> T: ...
    def stream_chat(
        self, messages: list[ChatMessage], config: GenerationConfig
    ) -> AsyncIterator[str]: ...
