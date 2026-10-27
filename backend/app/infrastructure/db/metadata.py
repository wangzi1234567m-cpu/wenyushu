"""Migration/test-only registry. Runtime modules must not import this module."""

from importlib import import_module

from app.infrastructure.db.base import Base

OWNERS = (
    "identity",
    "content",
    "exploration",
    "conversation",
    "discussion",
    "reading",
    "catalog",
    "handoff",
    "safety",
)
for owner in OWNERS:
    import_module(f"app.modules.{owner}.infrastructure.models")
metadata = Base.metadata
