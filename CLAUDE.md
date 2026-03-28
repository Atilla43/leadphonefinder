# TG Sales Bot — Web Platform

## Обзор проекта

Автоматизированная система продаж через Telegram. Бот (aiogram + Telethon + OpenRouter LLM) рассылает сообщения по базе ЛПР, ведёт AI-диалоги и продаёт услуги. Скраппер Яндекс.Карт и 2ГИС через Playwright собирает контакты.

**Текущий этап**: Разработка веб-платформы для аналитики, управления кампаниями и просмотра чатов.

> Подробная документация: `docs/01..06-*.md`

## Реальная архитектура

```
LeadPhoneFinder/
├── bot/                              # Telegram-бот
│   ├── main.py                       # Точка входа (aiogram polling)
│   ├── handlers/                     # Обработчики команд (aiogram Router)
│   │   ├── start.py                  # /start, /help, whitelist
│   │   ├── file_upload.py            # Загрузка Excel/CSV → обогащение
│   │   ├── callbacks.py              # Callback-кнопки меню
│   │   ├── scrapper.py               # FSM скраппинга
│   │   └── outreach.py               # FSM рассылки (главный handler)
│   ├── models/                       # Dataclasses
│   │   ├── company.py                # Company, EnrichmentResult
│   │   └── outreach.py               # OutreachCampaign, OutreachRecipient
│   ├── services/                     # Бизнес-логика
│   │   ├── outreach.py               # OutreachService — рассылка + listener + ping
│   │   ├── outreach_storage.py       # JSON-персистентность кампаний
│   │   ├── ai_sales.py               # AISalesEngine — LLM через OpenRouter
│   │   ├── account_pool.py           # Мульти-аккаунтный Telethon (round-robin)
│   │   ├── enrichment.py             # Обогащение через Sherlock API/Telegram
│   │   ├── sherlock_client.py        # Telethon-клиент для @sherlock_osint_bot
│   │   ├── sherlock_api.py           # HTTP API Sherlock (Dyxless)
│   │   ├── voice_transcriber.py      # Groq Whisper (транскрибация голосовых)
│   │   └── scrapper/                 # Скраппер компаний
│   │       ├── orchestrator.py       # Оркестратор: парсинг → скрап → дедупликация → ИНН
│   │       ├── twogis.py             # 2ГИС (Playwright)
│   │       ├── yandex_maps.py        # Яндекс.Карты (Playwright)
│   │       ├── query_parser.py       # "рестораны Сочи" → category + location
│   │       ├── deduplicator.py       # Дедупликация по названию + адрес
│   │       ├── inn_finder.py         # DaData API (ИНН, директор, юр. форма)
│   │       ├── cache.py              # Кеш в JSON (TTL 24ч)
│   │       └── models.py             # ScrapedCompany, ScrapperResult
│   ├── ui/                           # Клавиатуры и тексты (скраппер)
│   └── utils/                        # config.py (pydantic-settings), клавиатуры, сообщения
├── data/                             # Персистентное хранилище (JSON)
│   ├── outreach/                     # campaign_{user_id}_{campaign_id}.json
│   └── cache/                        # {category}_{location}.json
├── database/                         # SQLite (ПУСТАЯ — 0 байт, не используется)
├── web/                              # Веб-платформа (НЕ СОЗДАНА)
│   ├── frontend/                     # Next.js SPA
│   └── backend/                      # FastAPI REST API
├── tests/
├── scripts/
├── .env / .env.example
├── requirements.txt
└── deploy.sh                         # systemd-деплой на Ubuntu
```

## Хранение данных — КРИТИЧНО

> **SQLite БД пуста (0 байт). Все данные в JSON-файлах.**

| Данные | Путь | Формат |
|--------|------|--------|
| Кампании рассылки | `data/outreach/campaign_*.json` | OutreachCampaign + Recipients + Chat history |
| Кеш скраппера | `data/cache/{cat}_{loc}.json` | ScrapperResult + ScrapedCompany[] |
| Пул аккаунтов | `data/telethon_accounts.json` | AccountInfo[] |
| Результаты обогащения | in-memory `results_storage` | Теряется при рестарте |

### OutreachCampaign (JSON)
```
campaign_id, user_id, name, offer, status, recipients[], sent_count, warm_count,
rejected_count, not_found_count, manager_ids[], system_prompt, service_info
```
**Статусы:** pending → sending → listening → paused → completed/cancelled

### OutreachRecipient (в recipients[])
```
phone, company_name, contact_name, category, rating, reviews_count, website,
address, director_name, telegram_user_id, account_phone, status,
conversation_history[{role, content}], last_message_at, ping_count, error_message
```
**Статусы:** pending → sent → talking → warm → warm_confirmed / rejected / referral / no_response / not_found / error

### ScrapedCompany (JSON кеш)
```
name, address, source(2gis/yandex), phone, website, inn, category,
director_name, rating, reviews_count, working_hours, legal_form, legal_name
```

## Как работает бот

### AI-рассылка (главный модуль)

**Фаза 1 — Рассылка:**
Recipients → normalize_phone → ImportContacts (Telethon) → если в Telegram → отправка первого сообщения → задержка (растянуто на 10:00-17:00 МСК)

**Фаза 2a — Listener:**
Входящее сообщение → дебаунс 30 сек → AISalesEngine (OpenRouter GPT-4o-mini) → JSON {reply, status} → отправка → обновление статуса

**Фаза 2b — Автопинг:**
Каждые 4ч: если нет ответа → follow-up через LLM (макс 3 пинга)

**Особенности:**
- Round-robin мульти-аккаунт (AccountPool)
- Лимит 30 сообщений/день на аккаунт
- Транскрибация голосовых (Groq Whisper)
- Referral: лид дал контакт → LLM извлекает → пишем новому лиду
- Восстановление кампаний после рестарта

### Скраппер
QueryParser → [2ГИС + Яндекс.Карты] (Playwright) → Deduplicator → InnFinder (DaData) → Кеш JSON

## Веб-платформа — Функциональные требования

### 1. Дашборд аналитики
- KPI: отправлено, ответили, warm, rejected, конверсия
- Графики динамики по дням
- Воронка: pending → sent → talking → warm → warm_confirmed (+ rejected, no_response)
- Сравнение кампаний

### 2. Просмотр чатов в реальном времени
- Список диалогов с фильтрами (статус, кампания, дата)
- Полная история переписки (conversation_history)
- Реальные статусы: sent, talking, warm, warm_confirmed, rejected, referral, no_response
- Поиск по сообщениям
- WebSocket для live-обновлений (Этап 2)

### 3. Управление кампаниями
- Просмотр активных кампаний с детальной статистикой
- Список recipients с фильтрацией по статусу
- Пауза/возобновление (Этап 2 — через Redis IPC)
- Создание новых кампаний (Этап 3)

## Стратегия разработки веб-платформы

### Этап 1 — Read-Only Dashboard (MVP)
- FastAPI читает JSON-файлы из `data/outreach/` и `data/cache/`
- Бот не модифицируется, нет race conditions (только чтение)
- Фронтенд: дашборд + просмотр чатов + список кампаний

### Этап 2 — Общая БД + Real-time
- Миграция на SQLite/PostgreSQL
- Бот пишет в БД
- WebSocket через file watcher или Redis pub/sub
- Управление кампаниями через API

### Этап 3 — Полное управление
- Создание кампаний через web UI
- JWT-авторизация
- Webhook от бота для real-time

## API Endpoints (на основе реальных данных)

```
# Дашборд
GET  /api/dashboard/stats           — Агрегированная статистика из всех кампаний
GET  /api/dashboard/funnel          — Воронка по статусам recipients
GET  /api/dashboard/timeline        — Динамика по дням (из last_message_at)

# Кампании
GET  /api/campaigns                 — Список из data/outreach/*.json
GET  /api/campaigns/{id}            — Детали + recipients
GET  /api/campaigns/{id}/recipients — Recipients с фильтрами (?status=warm,talking)

# Диалоги
GET  /api/conversations             — Recipients с conversation_history, сортировка по last_message_at
GET  /api/conversations/{campaign_id}/{phone} — Полная история чата

# Лиды
GET  /api/leads                     — Уникальные лиды из всех кампаний
GET  /api/leads/stats               — Статистика по категориям и статусам

# Скраппер
GET  /api/scraper/cache             — Кешированные запросы
GET  /api/scraper/cache/{query}     — Компании из кеша

# Аккаунты (read-only, без секретов)
GET  /api/accounts                  — Список аккаунтов + sent_today
```

## Технические требования

### Стек
- **Frontend**: Next.js 14+ (App Router) + TypeScript + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI (Python) — единство с ботом
- **Графики**: Recharts или Tremor
- **Реальное время**: WebSocket (Этап 2)
- **Авторизация**: JWT (1 admin для начала)

### Дизайн — СТРОГО
- Тёмная тема, SaaS-стилистика
- Шрифт: Plus Jakarta Sans или Satoshi (**НЕ** Inter, **НЕ** Roboto)
- Палитра: тёмные фоны (#0a0a0f, #111118), один акцент (emerald/cyan)
- Glass-morphism карточки, тонкие бордеры, мягкие тени
- Анимации: плавные staggered fade-in
- Фиксированный sidebar слева
- Desktop-first, mobile-friendly

### Код
- Python: PEP 8, type hints, async/await
- TypeScript: strict, функциональные компоненты, hooks
- snake_case (Python), camelCase (TS), PascalCase (компоненты)
- Все секреты через .env
- CORS: localhost:3000 ↔ localhost:8000

### Git
- Формат: `feat(web): добавлен дашборд аналитики`
- Ветки: `feature/dashboard`, `feature/chat-viewer`, `feature/campaigns`

## Переменные окружения

**Обязательные:** BOT_TOKEN, TELETHON_API_ID/HASH/PHONE, OPENROUTER_API_KEY
**Скраппер:** DADATA_TOKEN, SCRAPPER_* настройки
**Рассылка:** OUTREACH_* лимиты и задержки
**Доп. AI:** GROQ_API_KEY (голосовые), LLM_* (парсинг запросов)
**Инфра:** REDIS_URL (опционально), ALLOWED_USER_IDS (whitelist)

> Полный список: `docs/05-environment.md` и `.env.example`

## Ограничения

1. **НЕ трогать** файлы бота (`bot/`) без явной просьбы
2. **Веб API читает JSON-файлы** бота — не создавать отдельную БД на Этапе 1
3. **НЕ хардкодить** секреты
4. **conversation_history не хранит timestamp** каждого сообщения — учитывать при разработке чата
5. **campaign_id может быть None** у старых кампаний (до добавления мульти-кампаний)
