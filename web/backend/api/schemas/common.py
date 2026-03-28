"""Общие схемы."""

from pydantic import BaseModel


class PaginatedParams(BaseModel):
    """Параметры пагинации."""
    offset: int = 0
    limit: int = 50


class PaginationMeta(BaseModel):
    """Мета-данные пагинации."""
    total: int
    offset: int
    limit: int
