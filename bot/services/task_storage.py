"""Персистентное хранилище задач обработки."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TaskStorage(ABC):
    """Абстрактный интерфейс хранилища задач."""

    @abstractmethod
    async def save_task(self, user_id: int, task_data: dict) -> str:
        """
        Сохраняет задачу для пользователя.

        Args:
            user_id: ID пользователя
            task_data: Данные задачи

        Returns:
            task_id: Идентификатор задачи
        """
        pass

    @abstractmethod
    async def get_task(self, user_id: int) -> Optional[dict]:
        """
        Получает задачу пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Данные задачи или None
        """
        pass

    @abstractmethod
    async def delete_task(self, user_id: int) -> bool:
        """
        Удаляет задачу пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            True если задача была удалена
        """
        pass

    @abstractmethod
    async def task_exists(self, user_id: int) -> bool:
        """
        Проверяет существование задачи.

        Args:
            user_id: ID пользователя

        Returns:
            True если задача существует
        """
        pass

    @abstractmethod
    async def cleanup_stale(self, max_age: timedelta) -> int:
        """
        Удаляет устаревшие задачи.

        Args:
            max_age: Максимальный возраст задачи

        Returns:
            Количество удалённых задач
        """
        pass


class InMemoryTaskStorage(TaskStorage):
    """In-memory хранилище (fallback если Redis недоступен)."""

    def __init__(self):
        self._tasks: dict[int, dict] = {}
        self._lock = asyncio.Lock()

    async def save_task(self, user_id: int, task_data: dict) -> str:
        async with self._lock:
            task_data["created_at"] = datetime.now().isoformat()
            self._tasks[user_id] = task_data
            return task_data.get("task_id", str(user_id))

    async def get_task(self, user_id: int) -> Optional[dict]:
        async with self._lock:
            return self._tasks.get(user_id)

    async def delete_task(self, user_id: int) -> bool:
        async with self._lock:
            if user_id in self._tasks:
                del self._tasks[user_id]
                return True
            return False

    async def task_exists(self, user_id: int) -> bool:
        async with self._lock:
            return user_id in self._tasks

    async def cleanup_stale(self, max_age: timedelta) -> int:
        async with self._lock:
            now = datetime.now()
            stale_users = []
            for user_id, task in self._tasks.items():
                created_at_str = task.get("created_at")
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str)
                    if now - created_at > max_age:
                        stale_users.append(user_id)
            for user_id in stale_users:
                del self._tasks[user_id]
            return len(stale_users)


class RedisTaskStorage(TaskStorage):
    """Redis-based хранилище задач."""

    def __init__(self, redis_url: str, ttl_seconds: int = 3600):
        self._redis_url = redis_url
        self._ttl = ttl_seconds
        self._redis = None

    async def _get_redis(self):
        """Lazy initialization Redis клиента."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self._redis_url)
                # Проверяем подключение
                await self._redis.ping()
                logger.info("Connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._redis

    def _make_key(self, user_id: int) -> str:
        """Создаёт ключ для Redis."""
        return f"leadfinder:task:{user_id}"

    def _serialize_task(self, task_data: dict) -> str:
        """Сериализует задачу (без несериализуемых объектов)."""
        serializable = {}
        for key, value in task_data.items():
            # Пропускаем asyncio объекты
            if key == "cancel_event":
                continue
            # Конвертируем Company объекты в dict
            if key == "companies":
                serializable[key] = [
                    c.to_dict() if hasattr(c, "to_dict") else str(c)
                    for c in value
                ]
            else:
                serializable[key] = value
        serializable["created_at"] = datetime.now().isoformat()
        return json.dumps(serializable, ensure_ascii=False)

    def _deserialize_task(self, data: str) -> dict:
        """Десериализует задачу."""
        return json.loads(data)

    async def save_task(self, user_id: int, task_data: dict) -> str:
        redis = await self._get_redis()
        key = self._make_key(user_id)
        serialized = self._serialize_task(task_data)
        await redis.setex(key, self._ttl, serialized)
        logger.debug(f"Saved task for user {user_id}")
        return task_data.get("task_id", str(user_id))

    async def get_task(self, user_id: int) -> Optional[dict]:
        redis = await self._get_redis()
        key = self._make_key(user_id)
        data = await redis.get(key)
        if data:
            return self._deserialize_task(data)
        return None

    async def delete_task(self, user_id: int) -> bool:
        redis = await self._get_redis()
        key = self._make_key(user_id)
        deleted = await redis.delete(key)
        if deleted:
            logger.debug(f"Deleted task for user {user_id}")
        return deleted > 0

    async def task_exists(self, user_id: int) -> bool:
        redis = await self._get_redis()
        key = self._make_key(user_id)
        return await redis.exists(key) > 0

    async def cleanup_stale(self, max_age: timedelta) -> int:
        """Redis автоматически удаляет по TTL, но можно почистить вручную."""
        # Redis TTL уже обеспечивает cleanup, возвращаем 0
        return 0

    async def close(self):
        """Закрывает соединение с Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# Глобальный экземпляр storage
_task_storage: Optional[TaskStorage] = None


async def get_task_storage() -> TaskStorage:
    """
    Возвращает инициализированное хранилище задач.

    Использует Redis если настроен, иначе in-memory.
    """
    global _task_storage

    if _task_storage is not None:
        return _task_storage

    from bot.utils.config import settings

    if settings.redis_url:
        try:
            _task_storage = RedisTaskStorage(
                settings.redis_url,
                settings.task_ttl_seconds,
            )
            # Проверяем подключение
            await _task_storage._get_redis()
            logger.info("Using Redis task storage")
        except Exception as e:
            logger.warning(f"Redis unavailable, falling back to in-memory: {e}")
            _task_storage = InMemoryTaskStorage()
    else:
        logger.info("Redis not configured, using in-memory task storage")
        _task_storage = InMemoryTaskStorage()

    return _task_storage
