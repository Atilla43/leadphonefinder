"""Эндпоинты кампаний."""

from fastapi import APIRouter, Depends, HTTPException, Query

from api.schemas.campaign import (
    CampaignDetail,
    CampaignListResponse,
    CampaignSummary,
    RecipientItem,
    RecipientsResponse,
)
from core.deps import get_data_reader
from services.data_reader import DataReader

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _campaign_id(c: dict) -> str:
    return c.get("campaign_id") or str(c.get("user_id", ""))


def _to_summary(c: dict) -> CampaignSummary:
    recipients = c.get("recipients", [])
    sent = c.get("sent_count", 0)
    replied = sum(
        1 for r in recipients
        if r.get("status") in ("talking", "warm", "warm_confirmed", "referral")
    )
    response_rate = (replied / sent * 100) if sent else 0.0

    return CampaignSummary(
        campaign_id=_campaign_id(c),
        name=c.get("name", ""),
        user_id=c.get("user_id", 0),
        status=c.get("status", "unknown"),
        recipients_total=len(recipients),
        sent_count=sent,
        warm_count=c.get("warm_count", 0),
        rejected_count=c.get("rejected_count", 0),
        not_found_count=c.get("not_found_count", 0),
        response_rate=round(response_rate, 2),
        has_system_prompt=bool(c.get("system_prompt")),
        has_service_info=bool(c.get("service_info")),
    )


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    status: str | None = Query(default=None),
    reader: DataReader = Depends(get_data_reader),
) -> CampaignListResponse:
    """Список всех кампаний."""
    campaigns = reader.get_all_campaigns()
    if status:
        allowed = {s.strip() for s in status.split(",")}
        campaigns = [c for c in campaigns if c.get("status") in allowed]
    return CampaignListResponse(campaigns=[_to_summary(c) for c in campaigns])


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: str,
    reader: DataReader = Depends(get_data_reader),
) -> CampaignDetail:
    """Детали кампании."""
    c = reader.get_campaign(campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    recipients = c.get("recipients", [])
    breakdown: dict[str, int] = {}
    for r in recipients:
        s = r.get("status", "pending")
        breakdown[s] = breakdown.get(s, 0) + 1

    return CampaignDetail(
        campaign_id=_campaign_id(c),
        name=c.get("name", ""),
        user_id=c.get("user_id", 0),
        status=c.get("status", "unknown"),
        offer=c.get("offer", ""),
        system_prompt=c.get("system_prompt", ""),
        service_info=c.get("service_info", ""),
        manager_ids=c.get("manager_ids", []),
        recipients_total=len(recipients),
        sent_count=c.get("sent_count", 0),
        warm_count=c.get("warm_count", 0),
        rejected_count=c.get("rejected_count", 0),
        not_found_count=c.get("not_found_count", 0),
        statuses_breakdown=breakdown,
    )


@router.get("/{campaign_id}/recipients", response_model=RecipientsResponse)
async def list_recipients(
    campaign_id: str,
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    reader: DataReader = Depends(get_data_reader),
) -> RecipientsResponse:
    """Список получателей кампании с фильтрами."""
    c = reader.get_campaign(campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    recipients = c.get("recipients", [])

    # Фильтрация по статусу
    if status:
        allowed = {s.strip() for s in status.split(",")}
        recipients = [r for r in recipients if r.get("status") in allowed]

    # Поиск по имени/компании
    if search:
        q = search.lower()
        recipients = [
            r for r in recipients
            if q in (r.get("company_name", "")).lower()
            or q in (r.get("contact_name", "") or "").lower()
        ]

    total = len(recipients)
    page = recipients[offset: offset + limit]

    items = [
        RecipientItem(
            phone=r.get("phone", ""),
            company_name=r.get("company_name", ""),
            contact_name=r.get("contact_name"),
            category=r.get("category"),
            status=r.get("status", "pending"),
            last_message_at=r.get("last_message_at"),
            messages_count=len(r.get("conversation_history", [])),
            ping_count=r.get("ping_count", 0),
            rating=r.get("rating"),
            address=r.get("address"),
            account_phone=r.get("account_phone"),
        )
        for r in page
    ]

    return RecipientsResponse(recipients=items, total=total, offset=offset, limit=limit)
