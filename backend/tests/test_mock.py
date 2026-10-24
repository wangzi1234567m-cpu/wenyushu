import asyncio

import pytest
from app.integrations.llm.mock import MockLLM
from app.integrations.llm.ports import GenerationConfig
from app.integrations.search.mock import MockSearch
from app.integrations.search.ports import SearchResult
from app.shared.errors import ApplicationError
from pydantic import BaseModel, ConfigDict, ValidationError


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int


def test_structured_mock_and_stream():
    mock = MockLLM({"count": 1}, ("a", "b"))
    assert asyncio.run(mock.generate_structured(Payload, [], GenerationConfig())).count == 1

    async def collect():
        return [chunk async for chunk in mock.stream_chat([], GenerationConfig())]

    assert asyncio.run(collect()) == ["a", "b"]
    with pytest.raises(ValidationError):
        asyncio.run(MockLLM({"count": "1"}).generate_structured(Payload, [], GenerationConfig()))


@pytest.mark.parametrize("mode,error", [("timeout", TimeoutError), ("error", ApplicationError)])
def test_external_failures(mode, error):
    with pytest.raises(error):
        asyncio.run(MockLLM(mode=mode).generate_structured(Payload, [], GenerationConfig()))
    with pytest.raises(error):
        asyncio.run(MockSearch(mode=mode).search("query"))


def test_search_fixtures_only():
    item = SearchResult("https://example.invalid/fixture", "fixture", "untrusted fixture")
    mock = MockSearch((item,))
    assert asyncio.run(mock.search("query")) == [item]
    assert asyncio.run(mock.fetch(item.url)) == item
    with pytest.raises(ApplicationError):
        asyncio.run(mock.fetch("https://not-in-fixtures.invalid"))
