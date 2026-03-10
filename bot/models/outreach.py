"""Модели данных для AI-продажника (outreach)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class OutreachRecipient:
    """Получатель рассылки."""

    phone: str
    company_name: str
    contact_name: Optional[str] = None
    telegram_user_id: Optional[int] = None
    status: str = "pending"  # pending, sent, talking, warm, rejected, no_response, not_found, error
    conversation_history: list[dict] = field(default_factory=list)  # [{role, content}]
    last_message_at: Optional[datetime] = None
    ping_count: int = 0
    error_message: Optional[str] = None


@dataclass
class OutreachCampaign:
    """Кампания AI-продажника."""

    user_id: int
    offer: str
    recipients: list[OutreachRecipient]
    status: str = "pending"  # pending, sending, listening, paused, completed, cancelled
    sent_count: int = 0
    warm_count: int = 0
    rejected_count: int = 0
    not_found_count: int = 0
    system_prompt: str = ""
