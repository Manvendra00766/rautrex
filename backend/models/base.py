from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, async_scoped_session
from sqlalchemy.orm import DeclarativeBase
from asyncio import current_task


# Centralized base class for all ORM models
# Using DeclarativeBase is the SQLAlchemy 2.0 recommended style
class Base(DeclarativeBase):
    pass


# Async engine is created once and reused (connection pooling)
# DATABASE_URL is read from app settings at runtime, not hardcoded here
engine = None
async_session_factory = None


def init_engine(database_url: str) -> None:
    """Initialize the async engine and session factory.

    Called once at startup from main.py. We create the engine here rather
    than at module level so we can read DATABASE_URL from Pydantic settings
    first — this avoids loading .env vars before Pydantic's config parsing.
    """
    global engine, async_session_factory
    engine = create_async_engine(
        database_url,
        echo=False,  # Set True for SQL query logging in development
        pool_pre_ping=True,  # Verify connections before use (resilience to drops)
    )
    # scoped_session ties sessions to the current asyncio task,
    # which prevents session bleed between concurrent requests
    async_session_factory = async_scoped_session(
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
        scopefunc=current_task,
    )


async def get_db() -> AsyncSession:
    """FastAPI dependency that provides a request-scoped async DB session.

    Using an async context manager ensures the session is properly closed
    even if an exception is raised during request handling.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all tables defined by ORM models. Idempotent — safe to call multiple times."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Run migrations for schema updates
        await _migrate_schema(conn)


async def _migrate_schema(conn):
    """Apply schema migrations for existing tables."""
    # Add total_invested and total_value columns to portfolios if they don't exist
    try:
        await conn.exec_driver_sql(
            """
            ALTER TABLE portfolios
            ADD COLUMN IF NOT EXISTS total_invested FLOAT,
            ADD COLUMN IF NOT EXISTS total_value FLOAT;
            """
        )
    except Exception:
        # Column may already exist or table doesn't exist yet - this is fine
        pass
