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

    # ФИО директора (из ЕГРЮЛ/DaData)
    director_name: Optional[str] = None

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

    def to_dict(self) -> dict:
        """Сериализация в словарь для кеша."""
        return {
            "name": self.name,
            "address": self.address,
            "source": self.source.value,
            "phone": self.phone,
            "website": self.website,
            "inn": self.inn,
            "external_id": self.external_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "category": self.category,
            "director_name": self.director_name,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "working_hours": self.working_hours,
            "scraped_at": self.scraped_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScrapedCompany":
        """Десериализация из словаря."""
        return cls(
            name=data["name"],
            address=data["address"],
            source=ScrapperSource(data["source"]),
            phone=data.get("phone"),
            website=data.get("website"),
            inn=data.get("inn"),
            external_id=data.get("external_id"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            category=data.get("category"),
            director_name=data.get("director_name"),
            rating=data.get("rating"),
            reviews_count=data.get("reviews_count"),
            working_hours=data.get("working_hours"),
            scraped_at=datetime.fromisoformat(data["scraped_at"]) if data.get("scraped_at") else datetime.now(),
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

    # Кеш
    from_cache: bool = False
    cached_at: Optional[datetime] = None

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

    def to_dict(self) -> dict:
        """Сериализация для кеша."""
        return {
            "query": self.query,
            "companies": [c.to_dict() for c in self.companies],
            "total_found": self.total_found,
            "from_twogis": self.from_twogis,
            "from_yandex": self.from_yandex,
            "duplicates_removed": self.duplicates_removed,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScrapperResult":
        """Десериализация из кеша."""
        companies = [ScrapedCompany.from_dict(c) for c in data.get("companies", [])]
        return cls(
            query=data["query"],
            companies=companies,
            total_found=data.get("total_found", 0),
            from_twogis=data.get("from_twogis", 0),
            from_yandex=data.get("from_yandex", 0),
            duplicates_removed=data.get("duplicates_removed", 0),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            finished_at=datetime.fromisoformat(data["finished_at"]) if data.get("finished_at") else None,
        )
