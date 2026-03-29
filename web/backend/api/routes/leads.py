"""Эндпоинты лидов."""

import re
from collections import defaultdict

from fastapi import APIRouter, Depends, Query

from api.schemas.lead import LeadItem, LeadStats, LeadsResponse
from core.deps import get_data_reader
from services.db_data_reader import DbDataReader

router = APIRouter(prefix="/api/leads", tags=["leads"])


def _normalize_phone(phone: str) -> str:
    """Нормализует телефон для дедупликации."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if not digits.startswith("7"):
        digits = "7" + digits
    return "+" + digits


async def _collect_leads(reader: DbDataReader) -> list[dict]:
    """Собирает уникальных лидов из всех кампаний."""
    leads_map: dict[str, dict] = {}  # normalized_phone → lead data

    for cid, r in await reader.get_all_recipients():
        phone = r.get("phone", "")
        if not phone:
            continue
        norm = _normalize_phone(phone)
        existing = leads_map.get(norm)

        if existing:
            # Обновляем если этот recipient свежее
            existing["campaigns_count"] += 1
            msgs = len(r.get("conversation_history", []))
            existing["total_messages"] += msgs
            # Берём последний статус по времени
            r_time = r.get("last_message_at") or ""
            if r_time > (existing.get("last_activity") or ""):
                existing["status"] = r.get("status", existing["status"])
                existing["last_activity"] = r_time
        else:
            leads_map[norm] = {
                "phone": norm,
                "company_name": r.get("company_name", ""),
                "contact_name": r.get("contact_name"),
                "category": r.get("category"),
                "status": r.get("status", "pending"),
                "campaigns_count": 1,
                "total_messages": len(r.get("conversation_history", [])),
                "last_activity": r.get("last_message_at"),
                "rating": r.get("rating"),
                "address": r.get("address"),
            }

    return list(leads_map.values())


@router.get("", response_model=LeadsResponse)
async def list_leads(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="last_activity"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    reader: DbDataReader = Depends(get_data_reader),
) -> LeadsResponse:
    """Уникальные лиды из всех кампаний."""
    leads = await _collect_leads(reader)

    if status:
        allowed = {s.strip() for s in status.split(",")}
        leads = [lead for lead in leads if lead["status"] in allowed]

    if category:
        q = category.lower()
        leads = [lead for lead in leads if q in (lead.get("category") or "").lower()]

    if search:
        q = search.lower()
        leads = [
            lead for lead in leads
            if q in lead.get("company_name", "").lower()
            or q in (lead.get("contact_name") or "").lower()
            or q in lead.get("phone", "")
        ]

    # Сортировка
    reverse = True
    if sort_by == "company_name":
        reverse = False
    leads.sort(key=lambda x: x.get(sort_by) or "", reverse=reverse)

    total = len(leads)
    page = leads[offset: offset + limit]

    return LeadsResponse(
        leads=[LeadItem(**lead) for lead in page],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/stats", response_model=LeadStats)
async def get_lead_stats(
    reader: DbDataReader = Depends(get_data_reader),
) -> LeadStats:
    """Статистика по лидам."""
    leads = await _collect_leads(reader)

    by_status: dict[str, int] = defaultdict(int)
    by_category: dict[str, int] = defaultdict(int)

    for lead in leads:
        by_status[lead["status"]] += 1
        cat = lead.get("category")
        if cat:
            by_category[cat] += 1

    return LeadStats(
        total=len(leads),
        by_status=dict(by_status),
        by_category=dict(by_category),
    )
