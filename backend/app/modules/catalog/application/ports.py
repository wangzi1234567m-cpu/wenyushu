from typing import Protocol


class BookCatalogPort(Protocol):
    def verified_samples(self, themes: list[str], limit: int) -> list[dict]: ...
