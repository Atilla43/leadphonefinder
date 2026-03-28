"""Dependency injection."""

from services.data_reader import DataReader
from core.config import settings

_data_reader: DataReader | None = None


def get_data_reader() -> DataReader:
    """Возвращает singleton DataReader."""
    global _data_reader
    if _data_reader is None:
        _data_reader = DataReader(
            outreach_dir=settings.outreach_dir,
            cache_dir=settings.cache_dir,
            accounts_file=settings.accounts_file,
            cache_ttl=settings.data_cache_ttl_seconds,
        )
    return _data_reader
