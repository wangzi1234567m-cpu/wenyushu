import json
from collections.abc import AsyncIterator

import httpx
from app.integrations.llm.ports import ChatMessage, GenerationConfig, T
from app.shared.errors import ApplicationError


class DeepSeekLLM:
    """Server-only adapter. Never forwards reasoning, provider errors or credentials."""

    def __init__(self, key: str | None, transport: httpx.AsyncBaseTransport | None = None):
        self._key = key
        self._transport = transport

    def _client(self, config):
        if not self._key:
            raise ApplicationError("MODEL_UNAVAILABLE", "AI暂时不可用，请稍后重试", True)
        return httpx.AsyncClient(
            base_url="https://api.deepseek.com",
            timeout=config.timeout_seconds,
            headers={"Authorization": "Bearer " + self._key},
            transport=self._transport,
        )

    def _body(self, messages, config, stream):
        return {
            "model": config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "max_tokens": config.max_output_tokens,
            "thinking": {"type": "disabled"},
        }

    async def generate_structured(
        self, schema: type[T], messages: list[ChatMessage], config: GenerationConfig
    ) -> T:
        try:
            async with self._client(config) as client:
                body = self._body(
                    [ChatMessage("system", "只返回符合要求的JSON对象。")] + messages, config, False
                )
                body["response_format"] = {"type": "json_object"}
                response = await client.post("/chat/completions", json=body)
                response.raise_for_status()
                choice = response.json()["choices"][0]
                if choice["finish_reason"] != "stop":
                    raise ValueError("Incomplete generation")
                return schema.model_validate_json(choice["message"]["content"], strict=True)
        except ApplicationError:
            raise
        except Exception:
            raise ApplicationError(
                "MODEL_UNAVAILABLE", "AI暂时无法完成回复，请重试", True
            ) from None

    async def stream_chat(
        self, messages: list[ChatMessage], config: GenerationConfig
    ) -> AsyncIterator[str]:
        try:
            completed, done = False, False
            async with self._client(config) as client:
                async with client.stream(
                    "POST", "/chat/completions", json=self._body(messages, config, True)
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            done = True
                            break
                        payload = json.loads(data)
                        for choice in payload.get("choices", []):
                            reason = choice.get("finish_reason")
                            if reason is not None:
                                if reason != "stop":
                                    raise ValueError("Incomplete generation")
                                completed = True
                            content = choice.get("delta", {}).get("content")
                            if content:
                                yield content
            if not completed or not done:
                raise ValueError("Interrupted generation")
        except ApplicationError:
            raise
        except Exception:
            raise ApplicationError(
                "MODEL_UNAVAILABLE", "AI回复中断，已保留完成的讨论，请重试", True
            ) from None
