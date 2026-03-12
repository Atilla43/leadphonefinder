from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class EnrichmentStatus(Enum):
    """Статус обогащения записи."""

    PENDING = "pending"  # Ожидает обработки
    SUCCESS = "success"  # Телефон найден
    NOT_FOUND = "not_found"  # Телефон не найден в источнике
    INVALID_INN = "invalid_inn"  # Некорректный ИНН
    ERROR = "error"  # Ошибка при запросе


@dataclass
class Company:
    """Данные компании."""

    inn: str
    name: str
    phone: Optional[str] = None
    status: EnrichmentStatus = EnrichmentStatus.PENDING
    raw_response: Optional[str] = None

    # Данные из скраппера для многоэтапного поиска
    director_name: Optional[str] = None  # ФИО директора из ЕГРЮЛ/DaData
    map_phone: Optional[str] = None  # Телефон из карт (для обратного пробива)

    # Данные из скраппера
    website: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    working_hours: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    legal_form: Optional[str] = None   # "ООО", "ИП", "ПАО"
    legal_name: Optional[str] = None   # Полное юр название

    # Расширенные данные из API
    emails: list[str] = field(default_factory=list)
    contact_names: list[str] = field(default_factory=list)  # ФИО контактов
    addresses: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)  # Источники данных (baseName)
    records_count: int = 0  # Количество найденных записей

    def to_dict(self) -> dict:
        """Преобразование в словарь для выгрузки."""
        return {
            "ИНН": self.inn,
            "Название": self.name,
            "Телефон": self.phone or "",
            "Телефон (карты)": self.map_phone or "",
            "Email": ", ".join(self.emails) if self.emails else "",
            "Сайт": self.website or "",
            "Контакты (ФИО)": ", ".join(self.contact_names[:3]) if self.contact_names else "",
            "Директор": self.director_name or "",
            "Адреса": ", ".join(self.addresses[:2]) if self.addresses else "",
            "Категория": self.category or "",
            "Рейтинг": self.rating or "",
            "Отзывов": self.reviews_count or "",
            "Время работы": self.working_hours or "",
            "Широта": self.latitude or "",
            "Долгота": self.longitude or "",
            "Форма юр лица": self.legal_form or "",
            "Юр название": self.legal_name or "",
            "Источники": ", ".join(set(self.sources)) if self.sources else "",
            "Записей найдено": self.records_count,
            "Статус": self.status.value,
        }


@dataclass
class EnrichmentResult:
    """Результат обогащения списка компаний."""

    companies: list[Company]
    total: int = 0
    success_count: int = 0
    not_found_count: int = 0
    invalid_count: int = 0
    error_count: int = 0
    processing_time_seconds: float = 0.0
    flood_wait_seconds: Optional[int] = None  # Если Telegram требует подождать
    was_interrupted: bool = False  # Если обработка была прервана

    def __post_init__(self):
        """Автоматический подсчёт статистики."""
        if self.total == 0:
            self.total = len(self.companies)
        if self.success_count == 0:
            self.success_count = sum(
                1 for c in self.companies if c.status == EnrichmentStatus.SUCCESS
            )
        if self.not_found_count == 0:
            self.not_found_count = sum(
                1 for c in self.companies if c.status == EnrichmentStatus.NOT_FOUND
            )
        if self.invalid_count == 0:
            self.invalid_count = sum(
                1 for c in self.companies if c.status == EnrichmentStatus.INVALID_INN
            )
        if self.error_count == 0:
            self.error_count = sum(
                1 for c in self.companies if c.status == EnrichmentStatus.ERROR
            )

    @property
    def success_rate(self) -> float:
        """Процент успешных обогащений."""
        if self.total == 0:
            return 0.0
        return (self.success_count / self.total) * 100


@dataclass
class ProcessingTask:
    """Задача обработки файла."""

    task_id: str
    user_id: int
    filename: str
    companies: list[Company]
    status: str = "pending"  # pending, processing, completed, cancelled
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[EnrichmentResult] = None


@dataclass
class HistoryEntry:
    """Запись в истории загрузок."""

    task_id: str
    user_id: int
    filename: str
    total: int
    success_count: int
    created_at: datetime
    result_excel: Optional[bytes] = None
    result_csv: Optional[bytes] = None
