"""Эндпоинты диалогов."""

from fastapi import APIRouter, Depends, HTTPException, Query

from api.schemas.conversation import (
    CampaignBrief,
    ConversationDetail,
    ConversationPreview,
    ConversationsResponse,
    LastMessage,
    MessageItem,
    RecipientInfo,
)
from core.deps import get_data_reader
from services.data_reader import DataReader

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _build_preview(campaign_id: str, r: dict) -> ConversationPreview:
    history = r.get("conversation_history", [])
    last_msg = None
    if history:
        last = history[-1]
        last_msg = LastMessage(role=last["role"], content=last["content"])

    # unread = последнее от user и нет ответа assistant после него
    unread = bool(history and history[-1].get("role") == "user")

    return ConversationPreview(
        campaign_id=campaign_id,
        phone=r.get("phone", ""),
        company_name=r.get("company_name", ""),
        contact_name=r.get("contact_name"),
        category=r.get("category"),
        status=r.get("status", "pending"),
        last_message_at=r.get("last_message_at"),
        messages_count=len(history),
        last_message=last_msg,
        unread=unread,
    )


@router.get("", response_model=ConversationsResponse)
async def list_conversations(
    status: str | None = Query(default=None),
    campaign_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    reader: DataReader = Depends(get_data_reader),
) -> ConversationsResponse:
    """Список диалогов (recipients с conversation_history)."""
    all_convs: list[tuple[str, dict]] = []

    for c in reader.get_all_campaigns():
        cid = c.get("campaign_id") or str(c.get("user_id", ""))
        if campaign_id and cid != campaign_id:
            continue
        for r in c.get("recipients", []):
            if not r.get("conversation_history"):
                continue
            all_convs.append((cid, r))

    # Фильтрация по статусу
    if status:
        allowed = {s.strip() for s in status.split(",")}
        all_convs = [(cid, r) for cid, r in all_convs if r.get("status") in allowed]

    # Поиск по тексту
    if search:
        q = search.lower()
        filtered: list[tuple[str, dict]] = []
        for cid, r in all_convs:
            if q in r.get("company_name", "").lower():
                filtered.append((cid, r))
                continue
            if q in (r.get("contact_name", "") or "").lower():
                filtered.append((cid, r))
                continue
            # Поиск по тексту сообщений
            for msg in r.get("conversation_history", []):
                if q in msg.get("content", "").lower():
                    filtered.append((cid, r))
                    break
        all_convs = filtered

    # Сортировка по last_message_at DESC
    def sort_key(item: tuple[str, dict]) -> str:
        return item[1].get("last_message_at") or ""

    all_convs.sort(key=sort_key, reverse=True)

    total = len(all_convs)
    page = all_convs[offset: offset + limit]

    conversations = [_build_preview(cid, r) for cid, r in page]
    return ConversationsResponse(
        conversations=conversations, total=total, offset=offset, limit=limit,
    )


@router.get("/{campaign_id}/{phone}", response_model=ConversationDetail)
async def get_conversation(
    campaign_id: str,
    phone: str,
    reader: DataReader = Depends(get_data_reader),
) -> ConversationDetail:
    """Полная переписка с лидом."""
    c = reader.get_campaign(campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Ищем recipient по телефону (нормализуем)
    normalized = phone.replace(" ", "").replace("-", "")
    recipient = None
    for r in c.get("recipients", []):
        r_phone = r.get("phone", "").replace(" ", "").replace("-", "")
        if r_phone == normalized or r_phone.endswith(normalized[-10:]):
            recipient = r
            break

    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    messages = [
        MessageItem(role=m["role"], content=m["content"])
        for m in recipient.get("conversation_history", [])
    ]

    cid = c.get("campaign_id") or str(c.get("user_id", ""))

    return ConversationDetail(
        recipient=RecipientInfo(
            phone=recipient.get("phone", ""),
            company_name=recipient.get("company_name", ""),
            contact_name=recipient.get("contact_name"),
            category=recipient.get("category"),
            rating=recipient.get("rating"),
            reviews_count=recipient.get("reviews_count"),
            website=recipient.get("website"),
            address=recipient.get("address"),
            status=recipient.get("status", "pending"),
            last_message_at=recipient.get("last_message_at"),
            ping_count=recipient.get("ping_count", 0),
            account_phone=recipient.get("account_phone"),
        ),
        messages=messages,
        campaign=CampaignBrief(
            campaign_id=cid,
            name=c.get("name", ""),
            offer=c.get("offer", ""),
        ),
    )
