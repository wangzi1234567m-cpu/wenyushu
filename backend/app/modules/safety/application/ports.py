import re
from typing import Protocol

from app.shared.errors import ApplicationError


class SafetyPort(Protocol):
    def check_supplement(self, text: str | None) -> None: ...


class BasicTextSafety:
    """Small deterministic P1 gate; not a complete production moderation service."""

    def check_supplement(self, text):
        if text and (
            "\x00" in text
            or re.search(r"如何(?:制造|制作).*?(?:炸弹|爆炸物)|提供.*?自杀方法", text)
        ):
            raise ApplicationError("CONTENT_BLOCKED", "这段补充暂无法处理，请调整表达")
