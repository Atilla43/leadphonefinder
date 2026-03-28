# Модели данных

## Хранение данных — РЕАЛЬНОЕ СОСТОЯНИЕ

> **SQLite БД пуста (0 байт).** Все данные хранятся в JSON-файлах и in-memory структурах.

### Персистентное хранилище (JSON-файлы)

| Хранилище | Путь | Модель | Описание |
|-----------|------|--------|----------|
| Кампании рассылки | `data/outreach/campaign_{user_id}_{campaign_id}.json` | `OutreachCampaign` | Полные данные кампании + recipients + история чатов |
| Кеш скраппера | `data/cache/{category}_{location}.json` | `ScrapperResult` | Кешированные результаты поиска компаний (TTL 24ч) |
| Пул аккаунтов | `data/telethon_accounts.json` | `AccountInfo[]` | Telethon-аккаунты для рассылки |

### In-memory (теряется при рестарте)

| Переменная | Файл | Тип | Описание |
|------------|------|-----|----------|
| `results_storage` | `handlers/callbacks.py` | `dict[int, dict]` | Результаты обогащения файлов (user_id → {companies}) |
| `processing_tasks` | `handlers/file_upload.py` | `dict[int, dict]` | Активные задачи обработки файлов |
| `active_outreach` | `services/outreach.py` | `dict[int, dict[str, OutreachService]]` | Активные сервисы рассылки |
| `active_tasks` | `handlers/scrapper.py` | `dict[int, ScrapperResult]` | Активные задачи скраппинга |

---

## Модели данных — Outreach (рассылка)

### OutreachCampaign (`bot/models/outreach.py`)

```
OutreachCampaign
├── user_id: int                    # Telegram user ID владельца
├── campaign_id: str                # Уникальный ID (формат: "20260315_143022")
├── name: str                       # Краткое название (первые 40 символов оффера)
├── offer: str                      # Текст оффера (первое сообщение)
├── status: str                     # Статус кампании (см. ниже)
├── recipients: list[OutreachRecipient]  # Список получателей
├── sent_count: int                 # Кол-во отправленных
├── warm_count: int                 # Кол-во "теплых" лидов
├── rejected_count: int             # Кол-во отказов
├── not_found_count: int            # Кол-во не найденных в Telegram
├── manager_ids: list[int]          # Telegram IDs менеджеров для уведомлений
├── system_prompt: str              # Кастомный системный промпт для LLM
└── service_info: str               # Информация об услугах и ценах для LLM
```

**Статусы кампании:**
- `pending` — создана, не запущена
- `sending` — идёт рассылка первых сообщений
- `listening` — рассылка завершена, слушаем ответы
- `paused` — приостановлена пользователем
- `completed` — завершена
- `cancelled` — отменена

### OutreachRecipient (`bot/models/outreach.py`)

```
OutreachRecipient
├── phone: str                      # Телефон лида
├── company_name: str               # Название компании
├── contact_name: str?              # ФИО контактного лица
├── category: str?                  # Категория бизнеса (из скраппера)
├── rating: float?                  # Рейтинг на картах
├── reviews_count: int?             # Кол-во отзывов
├── website: str?                   # Сайт
├── working_hours: str?             # Время работы
├── address: str?                   # Адрес
├── director_name: str?             # ФИО директора
├── telegram_user_id: int?          # Telegram ID (после resolve)
├── account_phone: str?             # С какого аккаунта отправлено
├── referral_context: str?          # Контекст переписки (для referral)
├── status: str                     # Статус получателя (см. ниже)
├── conversation_history: list[dict]  # История чата [{role, content}]
├── last_message_at: datetime?      # Время последнего сообщения
├── ping_count: int                 # Кол-во follow-up пингов
└── error_message: str?             # Текст ошибки (если status=error)
```

**Статусы получателя:**
- `pending` — ожидает отправки
- `sent` — сообщение отправлено, ответа нет
- `talking` — диалог идёт
- `warm` — лид заинтересован (LLM определил)
- `warm_confirmed` — лид подтверждён как тёплый
- `referral` — лид перенаправил на другого человека
- `rejected` — отказ (3+ явных отказа или бизнес закрыт)
- `no_response` — не ответил после max пингов
- `not_found` — телефон не зарегистрирован в Telegram
- `error` — ошибка при отправке

### conversation_history формат

```json
[
  {"role": "assistant", "content": "Здравствуйте, коротко по «Ресторан Пушкин»..."},
  {"role": "user", "content": "Добрый день, что предлагаете?"},
  {"role": "assistant", "content": "Продвижение карточки на картах..."},
  {"role": "user", "content": "[голосовое] да, интересно, расскажите подробнее"}
]
```

---

## Модели данных — Скраппер

### ScrapedCompany (`bot/services/scrapper/models.py`)

```
ScrapedCompany
├── name: str                       # Название компании
├── address: str                    # Адрес
├── source: ScrapperSource          # Источник: "2gis" | "yandex"
├── phone: str?                     # Телефон
├── website: str?                   # Сайт
├── inn: str?                       # ИНН (из DaData)
├── external_id: str?               # ID на карте
├── latitude: float?                # Широта
├── longitude: float?               # Долгота
├── category: str?                  # Категория
├── director_name: str?             # ФИО директора (из ЕГРЮЛ/DaData)
├── rating: float?                  # Рейтинг
├── reviews_count: int?             # Кол-во отзывов
├── working_hours: str?             # Время работы
├── legal_form: str?                # "ООО", "ИП", "ПАО"
├── legal_name: str?                # Полное юр название
└── scraped_at: datetime            # Дата скраппинга
```

### ScrapperResult (`bot/services/scrapper/models.py`)

```
ScrapperResult
├── query: str                      # Поисковый запрос
├── companies: list[ScrapedCompany]
├── total_found: int
├── from_twogis: int
├── from_yandex: int
├── duplicates_removed: int
├── started_at: datetime?
├── finished_at: datetime?
├── from_cache: bool
├── cached_at: datetime?
└── errors: list[str]
```

---

## Модели данных — Обогащение (Enrichment)

### Company (`bot/models/company.py`)

```
Company
├── inn: str                        # ИНН компании
├── name: str                       # Название
├── phone: str?                     # Найденный телефон
├── status: EnrichmentStatus        # pending | success | not_found | invalid_inn | error
├── raw_response: str?              # Сырой ответ от Sherlock
├── director_name: str?             # ФИО директора
├── map_phone: str?                 # Телефон из карт
├── website: str?
├── category: str?
├── rating: float?
├── reviews_count: int?
├── working_hours: str?
├── latitude: float?
├── longitude: float?
├── legal_form: str?
├── legal_name: str?
├── emails: list[str]
├── contact_names: list[str]
├── addresses: list[str]
├── sources: list[str]              # Базы данных (baseName из Sherlock)
└── records_count: int
```

---

## Модели данных — Аккаунты

### AccountInfo (`bot/services/account_pool.py`)

```
AccountInfo
├── phone: str                      # Номер телефона
├── api_id: int                     # Telegram API ID
├── api_hash: str                   # Telegram API Hash
├── session_name: str               # Имя файла сессии
└── active: bool                    # Активен ли аккаунт
```

---

## Реальные данные (на момент анализа)

### Кампании (`data/outreach/`)
- 1 кампания: 20 получателей, 14 отправлено, 1 warm, 3 rejected, 6 not_found

### Кеш скраппера (`data/cache/`)
| Файл | Компаний |
|------|----------|
| автосервисы_москва.json | 200 |
| рестораны_москва.json | 173 |
| рестораны_сочи.json | 10 |
| стоматологии_москва.json | 93 |
| фитнес_москва.json | 307 |
