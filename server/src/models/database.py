"""Compatibility wrapper for legacy database session import path."""

import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.settings import settings
from src.db.database import AsyncSessionLocal


class _LegacyAsyncSessionContext:
    """Create isolated async DB session per usage to avoid cross-loop pool reuse in tests."""

    def __init__(self, db_url: str):
        self._db_url = db_url
        self._engine = None
        self._session = None

    async def __aenter__(self):
        self._engine = create_async_engine(
            self._db_url,
            echo=False,
            poolclass=NullPool,
            pool_pre_ping=False,
        )
        factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        self._session = factory()
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        if self._session is not None:
            try:
                await self._session.close()
            except Exception:
                pass
        if self._engine is not None:
            try:
                await self._engine.dispose()
            except Exception:
                pass


def async_session():
    """
    Legacy callable session factory expected by old tests.
    In test env, return isolated session context to avoid event-loop conflicts.
    """
    env = (os.getenv("ENVIRONMENT") or settings.ENVIRONMENT or "").lower()
    if env == "test":
        db_url = (
            os.getenv("TEST_DATABASE_URL_ASYNC")
            or os.getenv("DATABASE_URL_ASYNC")
            or settings.database_url
        )
        return _LegacyAsyncSessionContext(db_url)
    return AsyncSessionLocal()

__all__ = ["async_session"]
