"""Файловый кеш результатов скраппинга."""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from bot.services.scrapper.models import ScrapperResult

logger = logging.getLogger(__name__)


class ScrapperCache:
    """Файловый JSON-кеш для результатов скраппинга."""

    def __init__(self, cache_dir: str = "data/cache", ttl_hours: int = 24) -> None:
        self._cache_dir = Path(cache_dir)
        self._ttl = timedelta(hours=ttl_hours)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_filename(self, category: str, location: str) -> Path:
        """Создаёт имя файла из категории и города."""
        key = f"{category.lower().strip()}_{location.lower().strip()}"
        # Заменяем небезопасные символы
        safe_key = re.sub(r"[^\w]", "_", key)
        return self._cache_dir / f"{safe_key}.json"

    def get(self, category: str, location: str) -> Optional[ScrapperResult]:
        """Получает результат из кеша. None если просрочен или нет."""
        filepath = self._make_filename(category, location)

        if not filepath.exists():
            return None

        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(data["cached_at"])

            if datetime.now() - cached_at > self._ttl:
                logger.info(f"Cache expired: {filepath.name}")
                filepath.unlink(missing_ok=True)
                return None

            result = ScrapperResult.from_dict(data)
            result.from_cache = True
            result.cached_at = cached_at
            logger.info(f"Cache hit: {filepath.name} ({len(result.companies)} companies)")
            return result

        except Exception as e:
            logger.warning(f"Cache read error ({filepath.name}): {e}")
            filepath.unlink(missing_ok=True)
            return None

    def save(self, category: str, location: str, result: ScrapperResult) -> None:
        """Сохраняет результат в кеш."""
        filepath = self._make_filename(category, location)

        try:
            data = result.to_dict()
            data["cached_at"] = datetime.now().isoformat()
            data["category"] = category
            data["location"] = location

            filepath.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"Cached: {filepath.name} ({len(result.companies)} companies)")

        except Exception as e:
            logger.error(f"Cache write error: {e}")

    def clear(self) -> int:
        """Удаляет все файлы кеша."""
        count = 0
        for f in self._cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        return count

    def cleanup_stale(self) -> int:
        """Удаляет просроченные записи."""
        count = 0
        for f in self._cache_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                cached_at = datetime.fromisoformat(data["cached_at"])
                if datetime.now() - cached_at > self._ttl:
                    f.unlink()
                    count += 1
            except Exception:
                f.unlink()
                count += 1
        return count
