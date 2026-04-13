from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

from waygate_core.config.schema import CoreSettings


def _build_database_url(settings: CoreSettings, driver: str) -> str:
    return (
        f"postgresql+{driver}://{settings.pg_user}:{settings.pg_password}"
        f"@{settings.pg_host}:{settings.pg_port}/{settings.pg_db}"
    )


def async_client(
    settings: CoreSettings | None = None,
) -> async_sessionmaker[AsyncSession]:
    cfg = settings or CoreSettings()
    url = _build_database_url(cfg, "asyncpg")
    engine = create_async_engine(url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


def sync_client(settings: CoreSettings | None = None) -> sessionmaker[Session]:
    cfg = settings or CoreSettings()
    url = _build_database_url(cfg, "psycopg2")
    engine = create_engine(url, pool_pre_ping=True)
    return sessionmaker(engine, expire_on_commit=False)
