"""Схемы дашборда."""

from pydantic import BaseModel


class DashboardStats(BaseModel):
    """Общая статистика."""
    total_campaigns: int = 0
    active_campaigns: int = 0
    total_recipients: int = 0
    total_sent: int = 0
    total_replied: int = 0
    total_warm: int = 0
    total_rejected: int = 0
    total_no_response: int = 0
    total_not_found: int = 0
    response_rate: float = 0.0
    conversion_rate: float = 0.0


class FunnelStage(BaseModel):
    """Этап воронки."""
    stage: str
    count: int
    label: str


class FunnelData(BaseModel):
    """Данные воронки."""
    stages: list[FunnelStage]


class TimelinePoint(BaseModel):
    """Точка на графике динамики."""
    date: str
    sent: int = 0
    replied: int = 0
    warm: int = 0
    rejected: int = 0


class TimelineData(BaseModel):
    """Данные графика."""
    points: list[TimelinePoint]
