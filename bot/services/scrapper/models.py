"""Модели данных для скраппера."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class ScrapperSource(Enum):
    """Источник данных."""
    TWOGIS = "2gis"
    YANDEX = "yandex"


@dataclass
class ScrapedCompany:
    """Спарсенная компания."""
    name: str
    address: str
    source: ScrapperSource

    # Контактные данные (из карт)
    phone: Optional[str] = None
    website: Optional[str] = None

    # Идентификаторы
    inn: Optional[str] = None
    external_id: Optional[str] = None  # ID на карте

    # Координаты
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Категория
    category: Optional[str] = None

    # Рейтинг и отзывы
    rating: Optional[float] = None
    reviews_count: Optional[int] = None

    # Время работы
    working_hours: Optional[str] = None

    # Метаданные
    scraped_at: datetime = field(default_factory=datetime.now)

    def __hash__(self) -> int:
        """Хеш для дедупликации."""
        return hash((self.name.lower(), self.address.lower()))

    def __eq__(self, other: object) -> bool:
        """Сравнение для дедупликации."""
        if not isinstance(other, ScrapedCompany):
            return False
        return (
            self.name.lower() == other.name.lower() and
            self.address.lower() == other.address.lower()
        )


@dataclass
class ScrapperResult:
    """Результат скраппинга."""
    query: str
    companies: list[ScrapedCompany]

    # Статистика
    total_found: int = 0
    from_twogis: int = 0
    from_yandex: int = 0
    duplicates_removed: int = 0

    # Время выполнения
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    # Ошибки
    errors: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Время выполнения в секундах."""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def success(self) -> bool:
        """Успешно ли выполнен скраппинг."""
        return len(self.companies) > 0 and len(self.errors) == 0
