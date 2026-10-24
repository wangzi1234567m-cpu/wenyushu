import os

from alembic import context
from app.infrastructure.db.metadata import metadata
from sqlalchemy import create_engine, pool

url = os.environ["DATABASE_URL"]
if context.is_offline_mode():
    context.configure(url=url, target_metadata=metadata, literal_binds=True, include_schemas=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata, include_schemas=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
