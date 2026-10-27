from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

EXPECTED_REVISION = "0003_daily_discussion"


def database_ready(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalars().all() == [EXPECTED_REVISION]
    except SQLAlchemyError:
        return False
