from dataclasses import dataclass

from app.infrastructure.db.health import database_ready
from app.infrastructure.settings.config import Settings
from app.integrations.llm.mock import MockLLM
from app.integrations.llm.ports import LLMPort
from app.integrations.search.mock import MockSearch
from app.integrations.search.ports import SearchPort
from app.modules.identity.application.ports import AuthorizationPort
from app.modules.identity.application.service import IdentityService
from app.modules.identity.domain.actor import OwnerAuthorization
from app.modules.identity.infrastructure.csrf import SignedCsrf
from app.modules.identity.infrastructure.repository import SqlIdentityUnitOfWork
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
        MockLLM(),
        MockSearch(),
    )
    return services, engine
