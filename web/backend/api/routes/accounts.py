"""Эндпоинты аккаунтов: CRUD + OTP-авторизация."""

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.account import (
    AccountCreate,
    AccountItem,
    AccountToggleResponse,
    OtpStartResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
)
from core.deps import get_outreach_manager

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("")
async def list_accounts(
    mgr=Depends(get_outreach_manager),
) -> dict:
    """Список Telethon-аккаунтов."""
    accounts = mgr.get_accounts()
    items = [AccountItem(**a) for a in accounts]
    active = sum(1 for a in items if a.active)
    connected = sum(1 for a in items if a.connected)
    return {
        "accounts": [a.model_dump() for a in items],
        "total_accounts": len(items),
        "active_accounts": active,
        "connected_accounts": connected,
    }


@router.post("", status_code=201)
async def add_account(
    body: AccountCreate,
    mgr=Depends(get_outreach_manager),
) -> dict:
    """Добавить новый аккаунт."""
    try:
        result = await mgr.add_account(body.phone, body.api_id, body.api_hash)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{phone}")
async def remove_account(
    phone: str,
    mgr=Depends(get_outreach_manager),
) -> dict:
    """Удалить аккаунт."""
    removed = await mgr.remove_account(phone)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Аккаунт {phone} не найден")
    return {"phone": phone, "message": "Аккаунт удалён"}


@router.put("/{phone}/toggle", response_model=AccountToggleResponse)
async def toggle_account(
    phone: str,
    mgr=Depends(get_outreach_manager),
) -> AccountToggleResponse:
    """Вкл/выкл аккаунт."""
    try:
        result = await mgr.toggle_account(phone)
        return AccountToggleResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{phone}/connect", response_model=OtpStartResponse)
async def start_connect(
    phone: str,
    mgr=Depends(get_outreach_manager),
) -> OtpStartResponse:
    """Начать OTP-авторизацию → отправить код на телефон."""
    try:
        result = await mgr.start_auth(phone)
        return OtpStartResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения: {e}")


@router.post("/{phone}/verify", response_model=OtpVerifyResponse)
async def verify_connect(
    phone: str,
    body: OtpVerifyRequest,
    mgr=Depends(get_outreach_manager),
) -> OtpVerifyResponse:
    """Верифицировать OTP-код (+ опционально 2FA пароль)."""
    try:
        result = await mgr.verify_auth(
            phone=phone,
            code=body.code,
            phone_code_hash=body.phone_code_hash,
            password=body.password,
        )
        return OtpVerifyResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
