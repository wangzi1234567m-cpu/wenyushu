import asyncio
import json

import httpx
import pytest
from app.integrations.llm.deepseek import DeepSeekLLM
from app.integrations.llm.ports import ChatMessage, GenerationConfig
from app.shared.errors import ApplicationError
from pydantic import BaseModel


def test_stream_only_public_content_and_normal_completion():
    def response(request):
        body = json.loads(request.content)
        assert body["thinking"] == {"type": "disabled"}
        assert request.url == "https://api.deepseek.com/chat/completions"
        data = [
            {"choices": [{"delta": {"reasoning_content": "private thought"}}]},
            {"choices": [{"delta": {"content": "你好"}, "finish_reason": None}]},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]},
        ]
        return httpx.Response(
            200, text="".join("data: " + json.dumps(d) + "\n\n" for d in data) + "data: [DONE]\n\n"
        )

    llm = DeepSeekLLM("test-only-key", httpx.MockTransport(response))

    async def run():
        return [
            c async for c in llm.stream_chat([ChatMessage("user", "hello")], GenerationConfig())
        ]

    assert asyncio.run(run()) == ["你好"]


@pytest.mark.parametrize(
    "text,status",
    [
        ('data: {"choices":[{"delta":{"content":"partial"}}]}\n\n', 200),
        ('data: {"choices":[{"delta":{},"finish_reason":"length"}]}\n\ndata: [DONE]\n\n', 200),
        ("data: broken-json\n\n", 200),
        ("provider error with secret-key", 401),
    ],
)
def test_provider_failures_are_sanitized(text, status):
    llm = DeepSeekLLM(
        "secret-key", httpx.MockTransport(lambda _: httpx.Response(status, text=text))
    )

    async def run():
        return [c async for c in llm.stream_chat([], GenerationConfig())]

    with pytest.raises(ApplicationError) as error:
        asyncio.run(run())
    assert error.value.code == "MODEL_UNAVAILABLE"
    assert "secret-key" not in str(error.value)


def test_structured_validation_timeout_and_missing_key():
    class Result(BaseModel):
        value: int

    def timeout(_):
        raise httpx.ReadTimeout("sensitive upstream error")

    for llm in [
        DeepSeekLLM(None),
        DeepSeekLLM("key", httpx.MockTransport(timeout)),
        DeepSeekLLM(
            "key",
            httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json={
                        "choices": [
                            {"finish_reason": "stop", "message": {"content": '{"value":"wrong"}'}}
                        ]
                    },
                )
            ),
        ),
    ]:
        with pytest.raises(ApplicationError):
            asyncio.run(llm.generate_structured(Result, [], GenerationConfig()))
