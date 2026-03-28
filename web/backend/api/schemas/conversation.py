"""Схемы диалогов."""

from pydantic import BaseModel


class MessageItem(BaseModel):
    """Одно сообщение."""
    role: str
    content: str


class LastMessage(BaseModel):
    """Последнее сообщение (превью)."""
    role: str
    content: str


class ConversationPreview(BaseModel):
    """Превью диалога в списке."""
    campaign_id: str
    phone: str
    company_name: str
    contact_name: str | None = None
    category: str | None = None
    status: str
    last_message_at: str | None = None
    messages_count: int = 0
    last_message: LastMessage | None = None
    unread: bool = False


class ConversationsResponse(BaseModel):
    """Список диалогов."""
    conversations: list[ConversationPreview]
    total: int
    offset: int
    limit: int


class RecipientInfo(BaseModel):
    """Инфо о получателе для панели чата."""
    phone: str
    company_name: str
    contact_name: str | None = None
    category: str | None = None
    rating: float | None = None
    reviews_count: int | None = None
    website: str | None = None
    address: str | None = None
    status: str
    last_message_at: str | None = None
    ping_count: int = 0
    account_phone: str | None = None


class CampaignBrief(BaseModel):
    """Краткая инфо о кампании."""
    campaign_id: str
    name: str
    offer: str = ""


class ConversationDetail(BaseModel):
    """Полная переписка."""
    recipient: RecipientInfo
    messages: list[MessageItem]
    campaign: CampaignBrief
