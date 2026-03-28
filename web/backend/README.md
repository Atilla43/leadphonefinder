# LeadPhoneFinder — Web Backend

FastAPI REST API для веб-платформы аналитики и управления кампаниями.

## Требования

- Python 3.11+

## Установка

```bash
cd web/backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

## Запуск

```bash
# Из директории web/backend/
uvicorn main:app --reload --port 8000
```

Сервер будет доступен на http://localhost:8000

## Проверка

```bash
curl http://localhost:8000/api/health
```

## API Endpoints

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/health` | Health check |
| GET | `/api/dashboard/stats` | Общая статистика |
| GET | `/api/dashboard/funnel` | Воронка продаж |
| GET | `/api/dashboard/timeline?days=30` | Динамика по датам |
| GET | `/api/campaigns` | Список кампаний |
| GET | `/api/campaigns/{id}` | Детали кампании |
| GET | `/api/campaigns/{id}/recipients` | Получатели кампании |
| GET | `/api/conversations` | Список диалогов |
| GET | `/api/conversations/{campaign_id}/{phone}` | История чата |
| GET | `/api/leads` | Список ЛПР |
| GET | `/api/leads/stats` | Статистика по ЛПР |
| GET | `/api/scraper/cache` | Список кеша скраппера |
| GET | `/api/scraper/cache/{file}` | Данные из кеша |
| GET | `/api/accounts` | Список аккаунтов |
| WS | `/api/ws/events` | WebSocket real-time |

## Переменные окружения

Опциональные (по умолчанию используются пути относительно корня проекта):

| Переменная | По умолчанию | Описание |
|-----------|-------------|----------|
| `WEB_OUTREACH_DIR` | `data/outreach/` | Папка с JSON кампаний |
| `WEB_CACHE_DIR` | `data/cache/` | Папка с кешем скраппера |
| `WEB_ACCOUNTS_FILE` | `data/telethon_accounts.json` | Файл аккаунтов |
| `WEB_DATA_CACHE_TTL_SECONDS` | `5` | TTL кеша DataReader |
| `WEB_WS_CHECK_INTERVAL_SECONDS` | `3.0` | Интервал file watcher |
| `WEB_CORS_ORIGINS` | `["http://localhost:3000", ...]` | Разрешённые CORS origins |

## Архитектура

- **DataReader** — читает JSON-файлы бота с mtime-кешированием
- **WebSocket** — polling file watcher рассылает события при изменении файлов кампаний
- **Без собственной БД** — все данные из JSON-файлов бота (read-only)
