"""Dependency injection."""

from core.config import settings
from services.db_data_reader import DbDataReader

_data_reader: DbDataReader | None = None
_outreach_manager = None  # OutreachManager, lazy import
_async_engine = None


def get_async_engine():
    """Возвращает singleton async engine."""
    global _async_engine
    if _async_engine is None:
        from db.engine import get_async_engine as _create
        _async_engine = _create(settings.db_path)
    return _async_engine


def get_data_reader() -> DbDataReader:
    """Возвращает singleton DbDataReader."""
    global _data_reader
    if _data_reader is None:
        engine = get_async_engine()
        _data_reader = DbDataReader(
            engine=engine,
            cache_dir=settings.cache_dir,
            accounts_file=settings.accounts_file,
        )
    return _data_reader


def get_outreach_manager():
    """Возвращает singleton OutreachManager (lazy import)."""
    global _outreach_manager
    if _outreach_manager is None:
        from services.outreach_manager import OutreachManager
        _outreach_manager = OutreachManager()
    return _outreach_manager
