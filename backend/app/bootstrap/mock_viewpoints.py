import json
from uuid import UUID

from app.integrations.llm.mock import MockLLM


class MockViewpointLLM(MockLLM):
    """Deterministic context-backed fixture; never presented as a real model."""

    async def generate_structured(self, schema, messages, config):
        self._check()
        data = json.loads(messages[-1].content)
        source = data["messages"][-1]
        content = source["content"].strip()
        items = (
            [{"content": content[:230], "source_message_ids": [UUID(source["id"])]}]
            if len(content) >= 12
            else []
        )
        return schema.model_validate({"items": items}, strict=True)
