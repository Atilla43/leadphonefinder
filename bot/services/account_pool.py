"""Пул Telethon-аккаунтов для мульти-аккаунтной рассылки."""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from telethon import TelegramClient
from telethon.errors import UserDeactivatedBanError

logger = logging.getLogger(__name__)

ACCOUNTS_FILE = Path("data/telethon_accounts.json")


@dataclass
class AccountInfo:
    """Информация об аккаунте Telethon."""
    phone: str
    api_id: int
    api_hash: str
    session_name: str
    active: bool = True


class AccountPool:
    """Пул Telethon-аккаунтов с round-robin распределением."""

    def __init__(self):
        self.accounts: list[AccountInfo] = []
        self.clients: dict[str, TelegramClient] = {}  # phone → client
        self.sent_today: dict[str, int] = {}  # phone → count
        self._robin_index: int = 0

    # ─── Загрузка / сохранение ───

    def _save(self) -> None:
        """Сохраняет список аккаунтов в JSON."""
        ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(a) for a in self.accounts]
        ACCOUNTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> None:
        """Загружает список аккаунтов из JSON."""
        if not ACCOUNTS_FILE.exists():
            self.accounts = []
            return
        try:
            data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
            self.accounts = [AccountInfo(**item) for item in data]
        except Exception as e:
            logger.error(f"Failed to load accounts: {e}")
            self.accounts = []

    # ─── Миграция из .env ───

    def migrate_from_env(self) -> bool:
        """Мигрирует текущий аккаунт из .env если пул пуст.
        Returns True если миграция произошла."""
        from bot.utils.config import settings

        if self.accounts:
            return False

        if not all([settings.telethon_api_id, settings.telethon_api_hash, settings.telethon_phone]):
            return False

        account = AccountInfo(
            phone=settings.telethon_phone,
            api_id=settings.telethon_api_id,
            api_hash=settings.telethon_api_hash,
            session_name=settings.telethon_session_name,
        )
        self.accounts.append(account)
        self._save()
        logger.info(f"Migrated account {settings.telethon_phone} from .env")
        return True

    # ─── Подключение ───

    async def connect_all(self) -> int:
        """Подключает все активные аккаунты. Возвращает кол-во подключённых."""
        self._load()
        self.migrate_from_env()

        connected = 0
        for account in self.accounts:
            if not account.active:
                continue
            if account.phone in self.clients:
                connected += 1
                continue
            try:
                client = TelegramClient(
                    account.session_name,
                    account.api_id,
                    account.api_hash,
                    lang_code="ru",
                    system_lang_code="ru-RU",
                )
                await client.start(phone=account.phone)
                self.clients[account.phone] = client
                self.sent_today[account.phone] = 0
                connected += 1
                logger.info(f"Connected account {account.phone}")
            except UserDeactivatedBanError:
                logger.error(f"Account {account.phone} is banned")
                account.active = False
                self._save()
            except Exception as e:
                logger.error(f"Failed to connect {account.phone}: {e}")
        return connected

    async def disconnect_all(self) -> None:
        """Отключает все клиенты."""
        for phone, client in self.clients.items():
            try:
                await client.disconnect()
            except Exception:
                pass
        self.clients.clear()

    # ─── Получение клиента ───

    def get_client(self, phone: str) -> Optional[TelegramClient]:
        """Получает клиент по номеру телефона."""
        return self.clients.get(phone)

    def get_next_available(self, daily_limit: int = 30) -> Optional[tuple[TelegramClient, AccountInfo]]:
        """Round-robin: следующий аккаунт у которого sent_today < limit."""
        active = [(a, self.clients[a.phone]) for a in self.accounts
                  if a.active and a.phone in self.clients]
        if not active:
            return None

        # Пробуем все аккаунты начиная с robin_index
        for i in range(len(active)):
            idx = (self._robin_index + i) % len(active)
            account, client = active[idx]
            if self.sent_today.get(account.phone, 0) < daily_limit:
                self._robin_index = (idx + 1) % len(active)
                return client, account
        return None

    def increment_sent(self, phone: str) -> None:
        """Увеличивает счётчик отправок для аккаунта."""
        self.sent_today[phone] = self.sent_today.get(phone, 0) + 1

    def reset_daily_counters(self) -> None:
        """Сбрасывает дневные счётчики."""
        for phone in self.sent_today:
            self.sent_today[phone] = 0
        logger.info("Daily send counters reset")

    def all_limits_reached(self, daily_limit: int = 30) -> bool:
        """Проверяет, достигнут ли лимит у всех аккаунтов."""
        active_phones = [a.phone for a in self.accounts if a.active and a.phone in self.clients]
        if not active_phones:
            return True
        return all(self.sent_today.get(p, 0) >= daily_limit for p in active_phones)

    def total_daily_capacity(self, daily_limit: int = 30) -> int:
        """Общая дневная ёмкость (кол-во аккаунтов × лимит)."""
        active_count = sum(1 for a in self.accounts if a.active and a.phone in self.clients)
        return active_count * daily_limit

    # ─── Управление аккаунтами ───

    def add_account(self, phone: str, api_id: int, api_hash: str) -> AccountInfo:
        """Добавляет новый аккаунт (без подключения)."""
        # Проверка дублей
        for a in self.accounts:
            if a.phone == phone:
                raise ValueError(f"Аккаунт {phone} уже добавлен")

        session_name = f"userbot_{phone.replace('+', '').replace(' ', '')}"
        account = AccountInfo(
            phone=phone,
            api_id=api_id,
            api_hash=api_hash,
            session_name=session_name,
        )
        self.accounts.append(account)
        self._save()
        logger.info(f"Added account {phone}")
        return account

    def remove_account(self, phone: str) -> bool:
        """Удаляет аккаунт из пула."""
        for i, a in enumerate(self.accounts):
            if a.phone == phone:
                self.accounts.pop(i)
                self.clients.pop(phone, None)
                self.sent_today.pop(phone, None)
                self._save()
                logger.info(f"Removed account {phone}")
                return True
        return False

    def get_active_accounts(self) -> list[AccountInfo]:
        """Список активных подключённых аккаунтов."""
        return [a for a in self.accounts if a.active and a.phone in self.clients]

    def get_all_clients(self) -> list[TelegramClient]:
        """Все подключённые клиенты."""
        return list(self.clients.values())

    # ─── Распределение получателей ───

    def assign_recipients(self, recipients: list, daily_limit: int = 30) -> None:
        """Round-robin распределение получателей по аккаунтам.
        Устанавливает account_phone для каждого recipient."""
        active = self.get_active_accounts()
        if not active:
            return

        for i, recipient in enumerate(recipients):
            if recipient.status != "pending":
                continue
            account = active[i % len(active)]
            recipient.account_phone = account.phone


# Глобальный пул
_pool: Optional[AccountPool] = None


def get_account_pool() -> AccountPool:
    """Возвращает глобальный пул аккаунтов."""
    global _pool
    if _pool is None:
        _pool = AccountPool()
    return _pool
