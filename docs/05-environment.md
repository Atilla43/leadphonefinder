# Переменные окружения и зависимости

## Переменные окружения (.env)

### Обязательные

| Переменная | Описание | Пример |
|------------|----------|--------|
| `BOT_TOKEN` | Telegram Bot Token (@BotFather) | `1234567890:ABC...` |

### Telethon (для рассылки и Sherlock)

| Переменная | Описание | Пример |
|------------|----------|--------|
| `TELETHON_API_ID` | API ID с my.telegram.org | `12345678` |
| `TELETHON_API_HASH` | API Hash | `abcdef1234...` |
| `TELETHON_PHONE` | Номер телефона аккаунта | `+79001234567` |
| `TELETHON_SESSION_NAME` | Имя файла сессии | `userbot_session` |

### Sherlock (поиск телефонов по ИНН)

| Переменная | Описание | Пример |
|------------|----------|--------|
| `SHERLOCK_BOT_USERNAME` | Username бота Sherlock | `sherlock_osint_bot` |
| `SHERLOCK_API_URL` | HTTP API (приоритет над Telegram) | `https://api-dyxless.cfd` |
| `SHERLOCK_API_KEY` | Токен API | `your_token` |

### AI / LLM

| Переменная | Описание | Пример |
|------------|----------|--------|
| `OPENROUTER_API_KEY` | API ключ OpenRouter (для AI-диалогов) | `sk-or-...` |
| `OPENROUTER_MODEL` | Модель для диалогов | `openai/gpt-4o-mini` |
| `GROQ_API_KEY` | API ключ Groq (транскрибация голосовых) | `gsk_...` |
| `LLM_PROVIDER` | Провайдер для скраппера (опционально) | `openai` / `gigachat` / `yandexgpt` |
| `LLM_API_KEY` | API ключ LLM провайдера | |
| `LLM_MODEL` | Модель LLM | `gpt-4o-mini` |

### Скраппер

| Переменная | Описание | По умолчанию |
|------------|----------|-------------|
| `SCRAPPER_MAX_RESULTS` | Макс. результатов с источника | `100` |
| `SCRAPPER_USE_TWOGIS` | Использовать 2ГИС | `true` |
| `SCRAPPER_USE_YANDEX` | Использовать Яндекс.Карты | `true` |
| `SCRAPPER_HEADLESS` | Headless режим браузера | `true` |
| `SCRAPPER_DELAY_MIN` | Мин. задержка между запросами (сек) | `1.0` |
| `SCRAPPER_DELAY_MAX` | Макс. задержка | `3.0` |
| `DADATA_TOKEN` | Токен DaData для поиска ИНН | |

### Outreach (рассылка)

| Переменная | Описание | По умолчанию |
|------------|----------|-------------|
| `OUTREACH_DELAY_MIN` | Мин. задержка между рассылками (сек) | `5.0` |
| `OUTREACH_DELAY_MAX` | Макс. задержка | `15.0` |
| `OUTREACH_REPLY_DELAY_MIN` | Мин. задержка перед ответом AI | `3.0` |
| `OUTREACH_REPLY_DELAY_MAX` | Макс. задержка ответа | `8.0` |
| `OUTREACH_DAILY_LIMIT` | Лимит сообщений на аккаунт/день | `30` |
| `OUTREACH_PING_INTERVAL_HOURS` | Интервал пинга (часы) | `4` |
| `OUTREACH_MAX_PINGS` | Макс. кол-во пингов | `3` |
| `OUTREACH_WORK_HOUR_START` | Начало рабочего дня (МСК) | `10` |
| `OUTREACH_WORK_HOUR_END` | Конец рабочего дня (МСК) | `17` |
| `OUTREACH_STICKER_PACK` | Стикерпак для приветствия | `catsunicmass` |
| `OUTREACH_STICKER_INDEX` | Индекс стикера | `33` |

### Лимиты и доступ

| Переменная | Описание | По умолчанию |
|------------|----------|-------------|
| `ALLOWED_USER_IDS` | Whitelist Telegram user IDs | `` (все) |
| `REQUEST_DELAY_SECONDS` | Задержка между запросами Sherlock | `3.0` |
| `MAX_FILE_SIZE_MB` | Макс. размер файла | `10` |
| `MAX_ROWS` | Макс. строк в файле | `100` |
| `HISTORY_RETENTION_DAYS` | Хранение истории (дни) | `7` |

### Redis (опционально)

| Переменная | Описание | По умолчанию |
|------------|----------|-------------|
| `REDIS_URL` | URL Redis | `None` (in-memory) |
| `TASK_TTL_SECONDS` | TTL задач в Redis | `3600` |

---

## Зависимости (requirements.txt)

```
# Telegram
aiogram==3.4.1              # Bot API фреймворк
telethon==1.34.0             # Userbot API (MTProto)

# Данные
pandas==2.2.0                # Обработка таблиц
openpyxl==3.1.2              # Чтение/запись Excel

# Конфигурация
pydantic-settings==2.1.0     # Типизированные настройки
python-dotenv==1.0.0         # Загрузка .env

# Асинхронность
aiofiles==23.2.1             # Асинхронный файловый I/O
aiohttp==3.9.0               # HTTP клиент (для LLM API, Sherlock API)

# Скраппер
playwright==1.40.0           # Headless-браузер

# Хранилище
redis==5.0.0                 # Redis (опционально)

# Тесты
pytest==8.0.0
pytest-asyncio==0.23.0
```

### Не указаны в requirements.txt, но используются

- `openai` — не используется напрямую (OpenRouter через aiohttp)
- `cryptg` — опционально для ускорения Telethon

---

## Деплой

### Сервер
- Ubuntu 24.04
- IP: `155.212.230.128`
- Путь: `/root/LeadPhoneFinder`
- Сервис: systemd `leadbot`

### Команды
```bash
# Деплой
bash deploy.sh

# Управление
systemctl restart leadbot
systemctl status leadbot
journalctl -u leadbot -f

# Удалённый деплой
python remote_deploy.py
```

### Необходимые директории
```
data/outreach/    # Кампании
data/cache/       # Кеш скраппера
```
