"""Схемы аккаунтов Telethon."""

from pydantic import BaseModel


class AccountCreate(BaseModel):
    """Добавление аккаунта."""
    phone: str
    api_id: int
    api_hash: str


class AccountItem(BaseModel):
    """Аккаунт в списке."""
    phone: str
    phone_masked: str
    active: bool
    connected: bool
    session_name: str
    sent_today: int
    daily_limit: int


class AccountToggleResponse(BaseModel):
    """Ответ на toggle."""
    phone: str
    active: bool
    message: str


class OtpStartResponse(BaseModel):
    """Ответ на начало OTP."""
    phone_code_hash: str
    message: str


class OtpVerifyRequest(BaseModel):
    """Запрос на верификацию OTP."""
    code: str
    phone_code_hash: str
    password: str | None = None


class OtpVerifyResponse(BaseModel):
    """Ответ на верификацию."""
    success: bool
    needs_2fa: bool = False
    message: str
