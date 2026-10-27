from app.modules.discussion.infrastructure.models import contexts_table as contexts
from app.shared.errors import ApplicationError
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert


class SqlDiscussionContexts:
    def __init__(self, factory):
        self.factory = factory

    def put(self, actor, key, exploration, context):
        with self.factory.begin() as s:
            s.execute(
                insert(contexts)
                .values(
                    actor_id=actor,
                    conversation_id=key,
                    exploration_id=exploration,
                    context_json=context,
                )
                .on_conflict_do_nothing()
            )

    def get(self, actor, key):
        with self.factory() as s:
            row = s.execute(
                select(contexts.c.context_json).where(
                    contexts.c.actor_id == actor, contexts.c.conversation_id == key
                )
            ).first()
            if not row:
                raise ApplicationError("NOT_FOUND", "讨论背景尚未就绪，请重新进入讨论", True)
            return row[0]

    def delete(self, actor, key):
        with self.factory.begin() as s:
            s.execute(
                delete(contexts).where(
                    contexts.c.actor_id == actor, contexts.c.conversation_id == key
                )
            )
