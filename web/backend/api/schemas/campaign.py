"""Схемы кампаний."""

from pydantic import BaseModel


class CampaignSummary(BaseModel):
    """Краткая информация о кампании."""
    campaign_id: str
    name: str
    user_id: int
    status: str
    recipients_total: int = 0
    sent_count: int = 0
    warm_count: int = 0
    rejected_count: int = 0
    not_found_count: int = 0
    response_rate: float = 0.0
    conversion_rate: float = 0.0
    has_system_prompt: bool = False
    has_service_info: bool = False


class CampaignListResponse(BaseModel):
    """Список кампаний."""
    campaigns: list[CampaignSummary]


class CampaignDetail(BaseModel):
    """Полные данные кампании."""
    campaign_id: str
    name: str
    user_id: int
    status: str
    offer: str = ""
    system_prompt: str = ""
    service_info: str = ""
    manager_ids: list[int] = []
    recipients_total: int = 0
    sent_count: int = 0
    warm_count: int = 0
    rejected_count: int = 0
    not_found_count: int = 0
    statuses_breakdown: dict[str, int] = {}


class RecipientItem(BaseModel):
    """Получатель в таблице."""
    phone: str
    company_name: str
    contact_name: str | None = None
    category: str | None = None
    status: str = "pending"
    last_message_at: str | None = None
    messages_count: int = 0
    ping_count: int = 0
    rating: float | None = None
    address: str | None = None
    account_phone: str | None = None


class RecipientsResponse(BaseModel):
    """Список получателей с пагинацией."""
    recipients: list[RecipientItem]
    total: int
    offset: int
    limit: int


class CampaignActionResponse(BaseModel):
    """Ответ на действие с кампанией (launch/pause/resume/cancel)."""
    campaign_id: str
    status: str
    message: str


class CampaignCreateResponse(BaseModel):
    """Результат создания кампании."""
    campaign_id: str
    recipients_count: int
