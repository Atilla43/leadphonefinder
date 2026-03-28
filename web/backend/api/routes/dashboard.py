"""Эндпоинты дашборда."""

from fastapi import APIRouter, Depends, Query

from api.schemas.dashboard import DashboardStats, FunnelData, FunnelStage, TimelineData, TimelinePoint
from core.deps import get_data_reader
from services.data_reader import DataReader
from services.stats import compute_dashboard_stats, compute_funnel, compute_timeline

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(reader: DataReader = Depends(get_data_reader)) -> DashboardStats:
    """Общая статистика из всех кампаний."""
    data = compute_dashboard_stats(reader)
    return DashboardStats(**data)


@router.get("/funnel", response_model=FunnelData)
async def get_funnel(reader: DataReader = Depends(get_data_reader)) -> FunnelData:
    """Воронка по статусам."""
    stages = compute_funnel(reader)
    return FunnelData(stages=[FunnelStage(**s) for s in stages])


@router.get("/timeline", response_model=TimelineData)
async def get_timeline(
    days: int = Query(default=30, ge=1, le=365),
    campaign_id: str | None = Query(default=None),
    reader: DataReader = Depends(get_data_reader),
) -> TimelineData:
    """Динамика по дням."""
    points = compute_timeline(reader, days=days, campaign_id=campaign_id)
    return TimelineData(points=[TimelinePoint(**p) for p in points])
