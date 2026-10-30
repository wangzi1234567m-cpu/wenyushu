from dataclasses import dataclass

from app.bootstrap.mock_viewpoints import MockViewpointLLM
from app.infrastructure.db.health import database_ready
from app.infrastructure.settings.config import Settings
from app.integrations.llm.deepseek import DeepSeekLLM
from app.integrations.llm.mock import MockLLM
from app.integrations.llm.ports import GenerationConfig, LLMPort
from app.integrations.search.mock import MockSearch
from app.integrations.search.ports import SearchPort
from app.modules.catalog.infrastructure.reader import SqlBookCatalog
from app.modules.content.application.ports import DailyQuestionReader
from app.modules.content.infrastructure.reader import SqlContentReader
from app.modules.conversation.application.service import ConversationRuntime
from app.modules.conversation.infrastructure.repository import SqlConversationRepository
from app.modules.discussion.application.service import DiscussionPolicy, DiscussionService
from app.modules.discussion.application.viewpoints import ViewpointService
from app.modules.discussion.infrastructure.repository import SqlDiscussionContexts
from app.modules.discussion.infrastructure.viewpoints import SqlViewpoints
from app.modules.exploration.application.service import ExplorationService
from app.modules.exploration.infrastructure.repository import SqlExplorationRepository
from app.modules.identity.application.ports import AuthorizationPort
from app.modules.identity.application.service import IdentityService
from app.modules.identity.domain.actor import OwnerAuthorization
from app.modules.identity.infrastructure.csrf import SignedCsrf
from app.modules.identity.infrastructure.repository import SqlIdentityUnitOfWork
from app.modules.reading.application.service import MockRecommendationPort, ReadingService
from app.modules.reading.infrastructure.repository import SqlReadingRepository
from app.modules.safety.application.ports import BasicTextSafety
from app.shared.health import HealthService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@dataclass
class Services:
    identity: IdentityService
    health: HealthService
    authorization: AuthorizationPort
    llm: LLMPort
    search: SearchPort
    content: DailyQuestionReader | None = None
    exploration: ExplorationService | None = None
    reading: ReadingService | None = None
    conversations: ConversationRuntime | None = None
    discussion: DiscussionService | None = None
    runtime: ConversationRuntime | None = None
    provider_mode: str = "mock"
    viewpoints: ViewpointService | None = None


def build_services(settings: Settings):
    engine = create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
        hide_parameters=True,
    )
    factory = sessionmaker(engine, expire_on_commit=False)
    services = Services(
        IdentityService(
            lambda: SqlIdentityUnitOfWork(factory),
            SignedCsrf(settings.csrf_secret.get_secret_value(), settings.csrf_ttl_seconds),
            settings.actor_ttl_seconds,
        ),
        HealthService(lambda: database_ready(engine)),
        OwnerAuthorization(),
        DeepSeekLLM(
            settings.deepseek_api_key.get_secret_value() if settings.deepseek_api_key else None
        )
        if settings.provider == "deepseek"
        else MockLLM(
            payload={
                "central_question": "爱情与自由",
                "current_view": "保留选择自由",
                "viewpoints": [],
                "changes": [],
                "constraints": [],
                "unresolved": [],
            },
            chunks=(
                "影响与控制的区别，在于对方还能不能拒绝。争取一次相处的机会，不等于替对方决定感情；即使能保证被爱，也未必能得到被自由选择的意义。这是结果和关系成立方式之间的区别。",
            ),
        ),
        MockSearch(),
    )
    services.content = SqlContentReader(factory)
    services.reading = ReadingService(
        SqlReadingRepository(factory), MockRecommendationPort(SqlBookCatalog(factory))
    )
    services.exploration = ExplorationService(
        SqlExplorationRepository(factory), services.content, services.reading, BasicTextSafety()
    )
    services.provider_mode = settings.provider
    conversations = SqlConversationRepository(factory)
    contexts = SqlDiscussionContexts(factory)
    services.runtime = ConversationRuntime(
        conversations,
        DiscussionPolicy(contexts, BasicTextSafety()),
        services.llm,
        GenerationConfig(
            model=settings.deepseek_model if settings.provider == "deepseek" else "mock",
            timeout_seconds=settings.chat_timeout_seconds,
            max_output_tokens=settings.chat_max_output_tokens,
        ),
        settings.chat_context_budget,
        settings.chat_daily_turn_limit,
        settings.chat_global_turn_limit,
    )
    services.conversations = services.runtime
    services.viewpoints = ViewpointService(
        SqlViewpoints(factory),
        services.runtime,
        contexts,
        BasicTextSafety(),
        services.llm if settings.provider == "deepseek" else MockViewpointLLM(),
        GenerationConfig(
            model=settings.deepseek_model if settings.provider == "deepseek" else "mock",
            timeout_seconds=min(settings.chat_timeout_seconds, 30),
            max_output_tokens=1024,
        ),
    )
    services.discussion = DiscussionService(
        services.runtime, contexts, services.exploration, services.content, services.viewpoints
    )
    return services, engine
