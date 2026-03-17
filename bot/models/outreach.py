"""Модели данных для AI-продажника (outreach)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class OutreachRecipient:
    """Получатель рассылки."""

    phone: str
    company_name: str
    contact_name: Optional[str] = None

    # Контекст из скраппера (для персонализации AI)
    category: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    website: Optional[str] = None
    working_hours: Optional[str] = None
    address: Optional[str] = None
    director_name: Optional[str] = None

    telegram_user_id: Optional[int] = None
    account_phone: Optional[str] = None  # с какого аккаунта отправлено
    status: str = "pending"  # pending, sent, talking, warm, rejected, referral, no_response, not_found, error
    conversation_history: list[dict] = field(default_factory=list)  # [{role, content}]
    last_message_at: Optional[datetime] = None
    ping_count: int = 0
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "phone": self.phone,
            "company_name": self.company_name,
            "contact_name": self.contact_name,
            "category": self.category,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "website": self.website,
            "working_hours": self.working_hours,
            "address": self.address,
            "director_name": self.director_name,
            "telegram_user_id": self.telegram_user_id,
            "account_phone": self.account_phone,
            "status": self.status,
            "conversation_history": self.conversation_history,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "ping_count": self.ping_count,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OutreachRecipient":
        last_msg = data.get("last_message_at")
        if last_msg:
            last_msg = datetime.fromisoformat(last_msg)
        return cls(
            phone=data["phone"],
            company_name=data["company_name"],
            contact_name=data.get("contact_name"),
            category=data.get("category"),
            rating=data.get("rating"),
            reviews_count=data.get("reviews_count"),
            website=data.get("website"),
            working_hours=data.get("working_hours"),
            address=data.get("address"),
            director_name=data.get("director_name"),
            telegram_user_id=data.get("telegram_user_id"),
            account_phone=data.get("account_phone"),
            status=data.get("status", "pending"),
            conversation_history=data.get("conversation_history", []),
            last_message_at=last_msg,
            ping_count=data.get("ping_count", 0),
            error_message=data.get("error_message"),
        )


@dataclass
class OutreachCampaign:
    """Кампания AI-продажника."""

    user_id: int
    offer: str
    recipients: list[OutreachRecipient]
    campaign_id: str = ""  # уникальный ID кампании (timestamp)
    name: str = ""  # краткое название для UI
    status: str = "pending"  # pending, sending, listening, paused, completed, cancelled
    sent_count: int = 0
    warm_count: int = 0
    rejected_count: int = 0
    not_found_count: int = 0
    manager_ids: list[int] = field(default_factory=list)  # Telegram IDs менеджеров для уведомлений
    system_prompt: str = ""

    def __post_init__(self):
        if not self.campaign_id:
            self.campaign_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        if not self.name:
            self.name = self.offer[:40].replace("\n", " ")

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "offer": self.offer,
            "recipients": [r.to_dict() for r in self.recipients],
            "campaign_id": self.campaign_id,
            "name": self.name,
            "status": self.status,
            "sent_count": self.sent_count,
            "warm_count": self.warm_count,
            "rejected_count": self.rejected_count,
            "not_found_count": self.not_found_count,
            "manager_ids": self.manager_ids,
            "system_prompt": self.system_prompt,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OutreachCampaign":
        recipients = [OutreachRecipient.from_dict(r) for r in data.get("recipients", [])]
        return cls(
            user_id=data["user_id"],
            offer=data["offer"],
            recipients=recipients,
            campaign_id=data.get("campaign_id", ""),
            name=data.get("name", ""),
            status=data.get("status", "pending"),
            sent_count=data.get("sent_count", 0),
            warm_count=data.get("warm_count", 0),
            rejected_count=data.get("rejected_count", 0),
            not_found_count=data.get("not_found_count", 0),
            manager_ids=data.get("manager_ids", []),
            system_prompt=data.get("system_prompt", ""),
        )
