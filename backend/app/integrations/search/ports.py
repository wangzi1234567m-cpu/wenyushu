from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str
    text: str


class SearchPort(Protocol):
    async def search(self, query: str) -> list[SearchResult]: ...
    async def fetch(self, url: str) -> SearchResult: ...
