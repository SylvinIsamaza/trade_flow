from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Base class for models
class Base(DeclarativeBase):
    pass


# Dependency to get database session
async def get_db() -> AsyncSession:
    """Async database session dependency."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()