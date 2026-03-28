# Архитектура API для веб-платформы

## Ключевая проблема

**SQLite БД пуста.** Все данные бота хранятся в JSON-файлах (`data/outreach/`, `data/cache/`). Веб-платформа должна учитывать это.

## Стратегия: поэтапная миграция

### Этап 1 — Read-Only Dashboard (MVP)

FastAPI читает JSON-файлы напрямую. Бот не модифицируется.

**Плюсы:** Быстрый запуск, бот не ломается.
**Минусы:** Race conditions при одновременном чтении/записи, нет real-time.

### Этап 2 — Общая БД

Бот пишет в SQLite/PostgreSQL. API читает из БД. Бот и API делят общий data layer.

### Этап 3 — Полное управление

API может создавать/управлять кампаниями, бот принимает команды через Redis pub/sub.

---

## API Endpoints (Этап 1 — на основе реальных данных)

### Дашборд

```
GET /api/dashboard/stats
```
Агрегация из всех campaign_*.json:
```json
{
  "total_campaigns": 1,
  "total_recipients": 20,
  "total_sent": 14,
  "total_warm": 1,
  "total_rejected": 3,
  "total_not_found": 6,
  "total_talking": 10,
  "conversion_rate": 7.14,
  "response_rate": 71.4
}
```

```
GET /api/dashboard/funnel
```
Воронка по статусам recipients из всех кампаний:
```json
{
  "pending": 0,
  "sent": 10,
  "talking": 0,
  "warm": 0,
  "warm_confirmed": 1,
  "rejected": 3,
  "no_response": 0,
  "not_found": 6,
  "error": 0
}
```

```
GET /api/dashboard/timeline?days=30
```
Динамика по дням (из `last_message_at` в recipients):
```json
[
  {"date": "2026-03-15", "sent": 5, "replies": 3, "warm": 0, "rejected": 1},
  {"date": "2026-03-16", "sent": 9, "replies": 7, "warm": 1, "rejected": 2}
]
```

### Кампании

```
GET /api/campaigns
```
Список из `data/outreach/*.json`:
```json
[
  {
    "campaign_id": "20260315_143022",
    "user_id": 590317122,
    "name": "Продвижение на картах",
    "status": "listening",
    "sent_count": 14,
    "warm_count": 1,
    "rejected_count": 3,
    "not_found_count": 6,
    "recipients_total": 20
  }
]
```

```
GET /api/campaigns/{campaign_id}
```
Полные данные кампании + список recipients (без conversation_history для экономии).

```
GET /api/campaigns/{campaign_id}/recipients
```
Список получателей с фильтрами:
- `?status=warm,talking` — фильтр по статусу
- `?search=ресторан` — поиск по company_name

### Диалоги (чаты)

```
GET /api/conversations
```
Все recipients с непустой `conversation_history`, сортировка по `last_message_at DESC`:
```json
[
  {
    "campaign_id": "20260315_143022",
    "phone": "+79001234567",
    "company_name": "Ресторан Пушкин",
    "contact_name": "Иван Петрович",
    "status": "warm_confirmed",
    "last_message_at": "2026-03-16T14:22:00Z",
    "messages_count": 8,
    "last_message_preview": "Да, давайте созвонимся"
  }
]
```
Фильтры: `?status=talking,warm`, `?campaign_id=...`, `?search=...`

```
GET /api/conversations/{campaign_id}/{phone}
```
Полная история переписки:
```json
{
  "recipient": { ... },
  "conversation_history": [
    {"role": "assistant", "content": "Здравствуйте...", "timestamp": null},
    {"role": "user", "content": "Добрый день...", "timestamp": null}
  ]
}
```

> **Проблема:** `conversation_history` не хранит timestamp каждого сообщения. Есть только `last_message_at`. Для полноценного чата нужно добавить timestamp в каждое сообщение.

### Лиды

```
GET /api/leads
```
Уникальные лиды (дедупликация по телефону) из всех кампаний:
```json
[
  {
    "phone": "+79001234567",
    "company_name": "Ресторан Пушкин",
    "contact_name": "Иван",
    "category": "Рестораны",
    "status": "warm_confirmed",
    "campaigns_count": 1,
    "last_activity": "2026-03-16T14:22:00Z"
  }
]
```

```
GET /api/leads/stats
```
Статистика по категориям, статусам:
```json
{
  "by_status": {"sent": 10, "warm_confirmed": 1, "rejected": 3},
  "by_category": {"Рестораны": 8, "Автосервисы": 12}
}
```

### Скраппер (кеш)

```
GET /api/scraper/cache
```
Список кешированных запросов:
```json
[
  {"query": "автосервисы Москва", "companies_count": 200, "cached_at": "2026-03-12T21:11:00"},
  {"query": "рестораны Москва", "companies_count": 173, "cached_at": "2026-03-12T21:34:00"}
]
```

```
GET /api/scraper/cache/{query}
```
Компании из кеша.

### Аккаунты (read-only)

```
GET /api/accounts
```
```json
[
  {
    "phone": "+7900***4567",
    "active": true,
    "sent_today": 14
  }
]
```

> **Безопасность:** api_id, api_hash, session_name не возвращаются.

---

## WebSocket (для Этапа 2+)

```
WS /api/ws/conversations
```
Push-уведомления при:
- Новое сообщение в диалоге
- Изменение статуса лида
- Прогресс рассылки

Реализация: File watcher на `data/outreach/` или Redis pub/sub.

---

## Необходимые изменения в боте для веб-платформы

### Минимальные (Этап 1)
Никаких. API читает JSON-файлы.

### Рекомендуемые (Этап 2)
1. **Timestamp в conversation_history** — добавить `timestamp` в каждое сообщение
2. **SQLite/PostgreSQL data layer** — общий для бота и API
3. **Event bus** — Redis pub/sub для real-time уведомлений
4. **campaign_id** — у текущей кампании `campaign_id: None` (старый формат)

### Желательные (Этап 3)
1. **API для управления кампаниями** — создание, пауза, стоп через API
2. **Авторизация** — JWT-токены, привязка к Telegram user
3. **Webhook от бота** — вместо file watcher
