"""Compatibility wrapper for legacy database import path."""

from src.db.database import AsyncSessionLocal, engine, get_db

__all__ = ["AsyncSessionLocal", "engine", "get_db"]
