from typing import Literal

from app.integrations.search.ports import SearchResult
from app.shared.errors import ApplicationError


class MockSearch:
    """Only caller-supplied fixtures, never network or fabricated evidence."""

    def __init__(
        self, results: tuple[SearchResult, ...] = (), mode: Literal["ok", "error", "timeout"] = "ok"
    ):
        self.results = results
        self.mode = mode

    def _check(self):
        if self.mode == "timeout":
            raise TimeoutError("Mock search timeout")
        if self.mode == "error":
            raise ApplicationError("SEARCH_UNAVAILABLE", "搜索暂时不可用", True)

    async def search(self, query: str) -> list[SearchResult]:
        self._check()
        return list(self.results)

    async def fetch(self, url: str) -> SearchResult:
        self._check()
        for item in self.results:
            if item.url == url:
                return item
        raise ApplicationError("SEARCH_UNAVAILABLE", "Mock 中没有该来源", True)
