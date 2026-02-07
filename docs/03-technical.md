# Техническая архитектура

## Общая схема

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TELEGRAM BOT (aiogram)                          │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   /start    │  │   /scrape   │  │  file_upload│  │  callbacks  │         │
│  │   /help     │  │  (поиск)    │  │  (Excel)    │  │  (кнопки)   │         │
│  └─────────────┘  └──────┬──────┘  └──────┬──────┘  └─────────────┘         │
└──────────────────────────┼────────────────┼─────────────────────────────────┘
                           │                │
                           ▼                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              SCRAPPER SERVICE                                 │
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  Query Parser   │  │  2GIS Scrapper  │  │ Yandex Scrapper │              │
│  │ + Typo Fix      │  │  (Playwright)   │  │  (Playwright)   │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                        │
│           └────────────────────┼────────────────────┘                        │
│                                ▼                                             │
│                    ┌─────────────────────┐                                   │
│                    │    Deduplicator     │                                   │
│                    │  (fuzzy matching)   │                                   │
│                    └──────────┬──────────┘                                   │
│                               │                                              │
│                    ┌──────────▼──────────┐                                   │
│                    │     INN Finder      │                                   │
│                    │ (DaData + ЕГРЮЛ)    │                                   │
│                    └──────────┬──────────┘                                   │
└───────────────────────────────┼──────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            ENRICHMENT SERVICE                                 │
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  INN Validator  │  │ Sherlock Client │  │ Phone Extractor │              │
│  │  (checksum)     │  │   (Telethon)    │  │    (regex)      │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└───────────────────────────────┼──────────────────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │  Result Generator   │
                    │   (Excel/CSV)       │
                    └─────────────────────┘
```

---

## Структура проекта

```
LeadPhoneFinder/
├── bot/
│   ├── main.py                    # Точка входа
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py               # /start, /help
│   │   ├── scrapper.py            # /scrape (поиск компаний)
│   │   ├── file_upload.py         # Загрузка Excel/CSV
│   │   └── callbacks.py           # Inline кнопки
│   ├── services/
│   │   ├── scrapper/              # Модуль парсинга
│   │   │   ├── __init__.py
│   │   │   ├── models.py          # ScrapedCompany, ScrapperResult
│   │   │   ├── query_parser.py    # Парсинг запросов + исправление опечаток
│   │   │   ├── twogis.py          # 2GIS Playwright scrapper
│   │   │   ├── yandex_maps.py     # Яндекс.Карты scrapper
│   │   │   ├── deduplicator.py    # Дедупликация (fuzzy matching)
│   │   │   ├── inn_finder.py      # Поиск ИНН (DaData/ЕГРЮЛ)
│   │   │   ├── orchestrator.py    # Координация компонентов
│   │   │   └── llm_parser.py      # LLM для сложных запросов (опционально)
│   │   ├── file_parser.py         # Парсинг Excel/CSV
│   │   ├── inn_validator.py       # Валидация ИНН
│   │   ├── phone_extractor.py     # Извлечение телефонов
│   │   ├── sherlock_client.py     # Клиент Sherlock (Telethon)
│   │   ├── enrichment.py          # Оркестрация обогащения
│   │   └── result_generator.py    # Генерация Excel
│   ├── models/
│   │   └── company.py             # Company, EnrichmentStatus
│   ├── ui/
│   │   ├── keyboards.py           # Inline клавиатуры
│   │   └── messages.py            # Текстовые сообщения
│   └── utils/
│       └── config.py              # Pydantic Settings
├── tests/
│   ├── test_inn_validator.py
│   ├── test_phone_extractor.py
│   └── test_scrapper.py
├── docs/                          # Документация
├── requirements.txt
├── .env.example
└── README.md
```

---

## Компоненты

### 1. Query Parser

**Файл:** `bot/services/scrapper/query_parser.py`

Парсит запросы пользователя с исправлением опечаток:

```python
@dataclass
class ParsedQuery:
    original: str           # "рестараны Сачи"
    category: str           # "рестораны"
    location: str           # "Сочи"
    latitude: float         # 43.6028
    longitude: float        # 39.7342
    corrected_location: str # "сачи" (оригинал с опечаткой)
    corrected_category: str # "рестараны" (оригинал с опечаткой)
```

**Алгоритм исправления опечаток:**
1. Расстояние Левенштейна между словами
2. Порог: 1 ошибка для коротких слов, 2-3 для длинных
3. Поддержка 30+ городов и синонимов категорий

### 2. 2GIS Scrapper

**Файл:** `bot/services/scrapper/twogis.py`

Парсит компании с 2ГИС через Playwright:

```python
class TwoGisScrapper:
    async def scrape(self, query: ParsedQuery) -> list[ScrapedCompany]:
        # 1. Запуск headless браузера
        # 2. Переход на 2gis.ru/search/{query}
        # 3. Скроллинг + сбор карточек
        # 4. Парсинг: название, адрес, телефон, рейтинг
```

**Антибан меры:**
- Ротация User-Agent (4 варианта)
- Случайные задержки 1-3 сек
- Удаление `navigator.webdriver`
- Эмуляция viewport 1920x1080

### 3. Deduplicator

**Файл:** `bot/services/scrapper/deduplicator.py`

Удаляет дубликаты из разных источников:

```python
class Deduplicator:
    def deduplicate(self, companies: list) -> tuple[list, int]:
        # Критерии дубликата:
        # 1. Одинаковый ИНН
        # 2. Одинаковый телефон (нормализованный)
        # 3. Похожее название + адрес (fuzzy > 85%)
```

**Нормализация:**
- Название: убираем ООО/ИП/ЗАО, кавычки
- Адрес: улица→ул, проспект→пр
- Телефон: +79161234567

### 4. INN Finder

**Файл:** `bot/services/scrapper/inn_finder.py`

Ищет ИНН по названию компании:

```python
class InnFinder:
    async def find_inn(self, company_name: str, address: str) -> Optional[str]:
        # 1. DaData API (если есть токен)
        # 2. ЕГРЮЛ nalog.ru (fallback)
```

### 5. Sherlock Client

**Файл:** `bot/services/sherlock_client.py`

Получает телефоны ЛПР через OSINT-бота:

```python
class SherlockClient:
    async def query(self, inn: str) -> Optional[str]:
        # 1. Отправляем ИНН боту @sherlock_search_bot
        # 2. Ждём ответ (timeout 30 сек)
        # 3. Парсим телефон из текста
```

### 6. INN Validator

**Файл:** `bot/services/inn_validator.py`

Валидирует ИНН по контрольной сумме:

```python
def validate_inn(inn: str) -> bool:
    if len(inn) == 10:  # Юридическое лицо
        coefficients = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        checksum = sum(int(inn[i]) * coefficients[i] for i in range(9))
        return int(inn[9]) == (checksum % 11) % 10
    elif len(inn) == 12:  # ИП
        # Две контрольные цифры
        ...
```

---

## Модели данных

### ScrapedCompany

```python
@dataclass
class ScrapedCompany:
    name: str                    # "Ресторан Причал"
    address: str                 # "ул. Морская, 15"
    source: ScrapperSource       # TWOGIS / YANDEX
    phone: Optional[str]         # "+7 862 123-45-67"
    inn: Optional[str]           # "2320123456"
    rating: Optional[float]      # 4.5
    reviews_count: Optional[int] # 234
    category: Optional[str]      # "Рестораны"
    website: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
```

### Company (для обогащения)

```python
@dataclass
class Company:
    inn: str
    name: str
    phone: Optional[str] = None  # Телефон ЛПР
    status: EnrichmentStatus = EnrichmentStatus.PENDING

class EnrichmentStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    INVALID_INN = "invalid_inn"
    ERROR = "error"
```

---

## Технологический стек

| Компонент | Технология | Версия |
|-----------|------------|--------|
| Бот | aiogram | 3.4.1 |
| Userbot | Telethon | 1.34.0 |
| Парсинг | Playwright | 1.40.0 |
| HTTP | aiohttp | 3.9.0 |
| Excel | pandas + openpyxl | 2.2.0 / 3.1.2 |
| Конфиг | pydantic-settings | 2.1.0 |
| Тесты | pytest + pytest-asyncio | 8.0.0 |

---

## API интеграции

### DaData (поиск ИНН)

```
POST https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party
Authorization: Token {api_key}

{"query": "Ресторан Причал Сочи", "count": 5}
```

**Лимиты:** 10,000 запросов/день бесплатно

### ЕГРЮЛ (fallback)

```
POST https://egrul.nalog.ru/
Content-Type: application/x-www-form-urlencoded

query=Ресторан+Причал&region=
```

**Лимиты:** Без ограничений, но медленнее

---

## Конфигурация

### Обязательные переменные

```env
# Telegram Bot
BOT_TOKEN=1234567890:ABCdef...

# Telethon (для Sherlock)
TELETHON_API_ID=12345678
TELETHON_API_HASH=abcdef...
TELETHON_PHONE=+79001234567

# Sherlock
SHERLOCK_BOT_USERNAME=sherlock_search_bot
```

### Опциональные переменные

```env
# DaData (ускоряет поиск ИНН)
DADATA_TOKEN=your_token

# LLM для сложных запросов
LLM_PROVIDER=gigachat
LLM_API_KEY=your_key

# Лимиты
MAX_ROWS=100
SCRAPPER_MAX_RESULTS=100
```

---

## Обработка ошибок

### Антибан

При блокировке IP:
1. Ротация User-Agent
2. Увеличение задержек
3. Использование прокси (опционально)

### Таймауты

| Операция | Таймаут |
|----------|---------|
| Sherlock запрос | 30 сек |
| Playwright страница | 30 сек |
| DaData API | 10 сек |
| ЕГРЮЛ | 15 сек |

### Логирование

```python
import logging
logger = logging.getLogger(__name__)

# Уровни:
# DEBUG - детали парсинга
# INFO - успешные операции
# WARNING - retry, fallback
# ERROR - критические ошибки
```
