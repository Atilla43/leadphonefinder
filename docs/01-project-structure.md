# Структура проекта LeadPhoneFinder

## Дерево файлов

```
LeadPhoneFinder/
├── bot/                              # Telegram-бот (aiogram + telethon)
│   ├── __init__.py
│   ├── main.py                       # Точка входа: запуск polling, восстановление кампаний
│   ├── handlers/                     # Обработчики команд и callback'ов
│   │   ├── __init__.py
│   │   ├── start.py                  # /start, /help, проверка доступа (whitelist)
│   │   ├── file_upload.py            # Загрузка Excel/CSV → обогащение через Sherlock
│   │   ├── callbacks.py              # Callback-кнопки: меню, шаблоны, скачивание
│   │   ├── scrapper.py               # FSM скраппинга: запрос → поиск → результаты
│   │   └── outreach.py               # FSM рассылки: файл → оффер → подтверждение → запуск
│   ├── models/                       # Модели данных (dataclasses)
│   │   ├── __init__.py
│   │   ├── company.py                # Company, EnrichmentResult, ProcessingTask, HistoryEntry
│   │   └── outreach.py               # OutreachRecipient, OutreachCampaign
│   ├── services/                     # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── outreach.py               # OutreachService — ядро рассылки + listener + ping
│   │   ├── outreach_storage.py       # OutreachStorage — JSON-персистентность кампаний
│   │   ├── ai_sales.py               # AISalesEngine — LLM (OpenRouter) для AI-диалогов
│   │   ├── account_pool.py           # AccountPool — мульти-аккаунтный Telethon (round-robin)
│   │   ├── enrichment.py             # Обогащение компаний через Sherlock (API/Telegram)
│   │   ├── sherlock_client.py        # Telethon-клиент для бота @sherlock_osint_bot
│   │   ├── sherlock_api.py           # HTTP API клиент Sherlock (Dyxless API)
│   │   ├── phone_extractor.py        # Извлечение телефонов из текста
│   │   ├── inn_validator.py          # Валидация ИНН
│   │   ├── file_parser.py            # Парсинг Excel/CSV файлов
│   │   ├── result_generator.py       # Генерация Excel/CSV результатов
│   │   ├── voice_transcriber.py      # Транскрибация голосовых (Groq Whisper)
│   │   ├── task_storage.py           # Redis/in-memory хранилище задач
│   │   └── scrapper/                 # Скраппер компаний с карт
│   │       ├── __init__.py
│   │       ├── orchestrator.py       # Оркестратор: парсинг → скраппинг → дедупликация → ИНН
│   │       ├── twogis.py             # Скраппер 2ГИС (Playwright)
│   │       ├── yandex_maps.py        # Скраппер Яндекс.Карт (Playwright)
│   │       ├── query_parser.py       # Парсинг запросов ("рестораны Сочи" → category+location)
│   │       ├── deduplicator.py       # Дедупликация компаний по названию+адресу
│   │       ├── inn_finder.py         # Поиск ИНН через DaData API
│   │       ├── llm_parser.py         # LLM-fallback для парсинга сложных запросов
│   │       ├── cache.py              # Кеш результатов скраппинга (JSON-файлы)
│   │       └── models.py             # ScrapedCompany, ScrapperResult, ScrapperSource
│   ├── ui/                           # UI компоненты бота
│   │   ├── __init__.py
│   │   ├── keyboards.py              # Inline-клавиатуры (скраппер, источники)
│   │   └── messages.py               # Шаблоны сообщений (UI-тексты)
│   └── utils/                        # Утилиты
│       ├── __init__.py
│       ├── config.py                 # Settings (pydantic-settings) — все переменные окружения
│       ├── keyboards.py              # Основные клавиатуры (главное меню, шаблоны)
│       └── messages.py               # Основные сообщения (welcome, help, ошибки)
├── data/                             # Данные (персистентность)
│   ├── outreach/                     # JSON-файлы кампаний рассылки
│   │   └── campaign_{user_id}_{campaign_id}.json
│   └── cache/                        # Кеш скраппера (JSON)
│       ├── автосервисы_москва.json
│       ├── рестораны_москва.json
│       ├── рестораны_сочи.json
│       ├── стоматологии_москва.json
│       └── фитнес_москва.json
├── database/                         # SQLite (ПУСТАЯ, не используется)
│   └── data.db                       # 0 байт
├── scripts/                          # Утилитарные скрипты
│   └── migrate_campaign.py           # Миграция данных кампаний
├── tests/                            # Тесты
│   ├── __init__.py
│   ├── test_file_parser.py
│   ├── test_inn_validator.py
│   ├── test_phone_extractor.py
│   └── test_scrapper.py
├── web/                              # Веб-платформа (НЕ СОЗДАНА — планируется)
│   ├── frontend/                     # React/Next.js SPA
│   └── backend/                      # FastAPI REST API
├── .env                              # Переменные окружения (секреты)
├── .env.example                      # Пример .env
├── .gitignore
├── CLAUDE.md                         # Инструкции для Claude
├── README.md
├── requirements.txt                  # Python-зависимости
├── deploy.sh                         # Деплой на Ubuntu (systemd)
├── remote_deploy.py                  # Удалённый деплой
├── auth_telethon.py                  # Авторизация Telethon-сессии
├── fetch_dialogs.py                  # Дамп диалогов
├── find_lead.py                      # Поиск лида
├── fix_derpizza.py                   # Фикс данных
├── userbot_session.session           # Telethon-сессия (бинарный файл)
└── bot_live.log                      # Лог работы бота
```

## Ключевые наблюдения

1. **SQLite БД не используется** — `database/data.db` пуст (0 байт). Все данные хранятся в JSON-файлах.
2. **Веб-платформа отсутствует** — папка `web/` ещё не создана.
3. **Бот полностью функционален** — рассылка, AI-диалоги, скраппинг, обогащение работают.
4. **Деплой на VPS** — systemd-сервис на Ubuntu, сервер `155.212.230.128`.
