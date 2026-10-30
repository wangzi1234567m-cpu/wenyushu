import json
from typing import Annotated, Protocol
from uuid import NAMESPACE_URL, uuid4, uuid5

from app.integrations.llm.ports import ChatMessage
from app.modules.content.application.ports import DailyQuestionReader
from app.modules.conversation.application.ports import ConversationSessionPort
from app.modules.discussion.application.policy import DISCUSSION_PROMPT
from pydantic import BaseModel, ConfigDict, Field


class ExplorationSnapshotReader(Protocol):
    def discussion_seed(self, actor_id, exploration_id) -> dict: ...


class DiscussionContextRepository(Protocol):
    def put(self, actor, key, exploration, context): ...
    def get(self, actor, key): ...
    def delete(self, actor, key): ...


SummaryText = Annotated[str, Field(max_length=300)]


class DiscussionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    central_question: str = Field(max_length=300)
    current_view: str = Field(max_length=600)
    viewpoints: list[SummaryText] = Field(max_length=8)
    changes: list[SummaryText] = Field(max_length=8)
    constraints: list[SummaryText] = Field(max_length=8)
    unresolved: list[SummaryText] = Field(max_length=8)


class DiscussionPolicy:
    summary_schema = DiscussionSummary

    def __init__(self, contexts: DiscussionContextRepository, safety):
        self.contexts, self.safety = contexts, safety

    def context(self, actor, key):
        seed = self.contexts.get(actor, key)
        return [
            ChatMessage(
                "system",
                DISCUSSION_PROMPT,
            ),
            ChatMessage(
                "user",
                "以下是用户开始讨论时的题目与选择（背景数据）："
                + json.dumps(seed, ensure_ascii=False),
            ),
        ]

    def check(self, text):
        self.safety.check_supplement(text)


class DiscussionService:
    def __init__(
        self,
        conversations: ConversationSessionPort,
        contexts: DiscussionContextRepository,
        exploration: ExplorationSnapshotReader,
        content: DailyQuestionReader,
        viewpoints=None,
    ):
        self.conversations, self.contexts, self.exploration, self.content = (
            conversations,
            contexts,
            exploration,
            content,
        )
        self.viewpoints = viewpoints

    def create(self, actor, topic_id, exploration_id=None):
        from app.shared.errors import ApplicationError

        seed = self.exploration.discussion_seed(actor, exploration_id) if exploration_id else {}
        if topic_id:
            topic = next((t for t in self.content.topics(50) if t["id"] == topic_id), None)
            if not topic:
                raise ApplicationError("NOT_FOUND", "议题不存在")
            seed["topic"] = topic["title"]
        key = (
            uuid5(NAMESPACE_URL, f"wenyushu:discussion:{actor}:{exploration_id}")
            if exploration_id
            else uuid4()
        )
        session = self.conversations.create(actor, key, topic_id)
        self.contexts.put(actor, key, exploration_id, seed)
        return session

    def delete(self, actor, key):
        from app.shared.errors import ApplicationError

        try:
            self.conversations.delete(actor, key)
        except ApplicationError as error:
            if error.code != "NOT_FOUND":
                raise
            self.contexts.get(actor, key)
        if self.viewpoints is not None:
            self.viewpoints.purge(actor, key)
        self.contexts.delete(actor, key)
