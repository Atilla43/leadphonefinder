"""Эндпоинты аккаунтов (read-only)."""

from fastapi import APIRouter, Depends

from core.deps import get_data_reader
from services.data_reader import DataReader

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("")
async def list_accounts(
    reader: DataReader = Depends(get_data_reader),
) -> dict:
    """Список Telethon-аккаунтов (без секретов)."""
    accounts = reader.get_accounts()
    active = sum(1 for a in accounts if a.get("active"))
    return {
        "accounts": accounts,
        "total_accounts": len(accounts),
        "active_accounts": active,
    }
