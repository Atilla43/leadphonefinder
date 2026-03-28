"""Схемы лидов."""

from pydantic import BaseModel


class LeadItem(BaseModel):
    """Лид в таблице."""
    phone: str
    company_name: str
    contact_name: str | None = None
    category: str | None = None
    status: str
    campaigns_count: int = 1
    total_messages: int = 0
    last_activity: str | None = None
    rating: float | None = None
    address: str | None = None


class LeadsResponse(BaseModel):
    """Список лидов."""
    leads: list[LeadItem]
    total: int
    offset: int
    limit: int


class LeadStats(BaseModel):
    """Статистика по лидам."""
    total: int = 0
    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
