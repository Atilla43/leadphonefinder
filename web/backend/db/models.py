"""SQLAlchemy ORM модели для Signal Grid."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, default="")
    offer: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    warm_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    not_found_count: Mapped[int] = mapped_column(Integer, default=0)
    manager_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    service_info: Mapped[str] = mapped_column(Text, default="")
    work_hour_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_hour_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    recipients: Mapped[list["Recipient"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Campaign {self.campaign_id} [{self.status}]>"


class Recipient(Base):
    __tablename__ = "recipients"
    __table_args__ = (
        UniqueConstraint("campaign_id", "phone", name="uq_campaign_phone"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[str] = mapped_column(
        String, ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), index=True
    )
    phone: Mapped[str] = mapped_column(String, nullable=False)
    company_name: Mapped[str] = mapped_column(String, default="")
    contact_name: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviews_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    working_hours: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    director_name: Mapped[str | None] = mapped_column(String, nullable=True)
    telegram_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    account_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    referral_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ping_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped["Campaign"] = relationship(back_populates="recipients")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="recipient", cascade="all, delete-orphan", order_by="Message.id"
    )

    def __repr__(self) -> str:
        return f"<Recipient {self.phone} [{self.status}]>"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipients.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)  # 'assistant' / 'user'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    recipient: Mapped["Recipient"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.id} [{self.role}]>"


class Account(Base):
    __tablename__ = "accounts"

    phone: Mapped[str] = mapped_column(String, primary_key=True)
    api_id: Mapped[int] = mapped_column(Integer, nullable=False)
    api_hash: Mapped[str] = mapped_column(String, nullable=False)
    session_name: Mapped[str] = mapped_column(String, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Account {self.phone} active={self.active}>"
