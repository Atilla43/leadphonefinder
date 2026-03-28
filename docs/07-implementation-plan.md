# План реализации веб-платформы

## 1. Структура папок

### Backend (FastAPI)

```
web/backend/
├── main.py                          # FastAPI app, CORS, include_router
├── requirements.txt                 # fastapi, uvicorn, pydantic, watchdog
├── core/
│   ├── __init__.py
│   ├── config.py                    # Settings: DATA_DIR, CORS_ORIGINS, WS poll interval
│   └── deps.py                      # Dependency injection: get_data_reader()
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── dashboard.py             # GET /api/dashboard/stats|funnel|timeline
│   │   ├── campaigns.py             # GET /api/campaigns, /api/campaigns/{id}
│   │   ├── conversations.py         # GET /api/conversations, /api/conversations/{id}/{phone}
│   │   ├── leads.py                 # GET /api/leads, /api/leads/stats
│   │   ├── scraper.py               # GET /api/scraper/cache
│   │   ├── accounts.py              # GET /api/accounts
│   │   └── ws.py                    # WS /api/ws/events
│   └── schemas/
│       ├── __init__.py
│       ├── dashboard.py             # DashboardStats, FunnelData, TimelinePoint
│       ├── campaign.py              # CampaignSummary, CampaignDetail, RecipientItem
│       ├── conversation.py          # ConversationPreview, ConversationDetail, Message
│       ├── lead.py                  # LeadItem, LeadStats
│       └── common.py                # PaginatedResponse, StatusEnum
└── services/
    ├── __init__.py
    ├── data_reader.py               # Singleton: чтение JSON + кеш по file mtime
    ├── stats.py                     # Агрегация: воронка, timeline, KPI
    └── ws_manager.py                # ConnectionManager + file watcher (watchdog)
```

### Frontend (Next.js 14 App Router)

```
web/frontend/
├── next.config.js
├── tailwind.config.ts               # Тёмная тема, кастомные цвета
├── tsconfig.json
├── package.json
├── public/
│   └── favicon.ico
└── src/
    ├── app/
    │   ├── layout.tsx               # RootLayout: шрифт, ThemeProvider, Sidebar
    │   ├── page.tsx                 # redirect → /dashboard
    │   ├── globals.css              # Tailwind base + тёмная палитра + glass-morphism
    │   ├── dashboard/
    │   │   ├── page.tsx             # Server Component → загрузка initial data
    │   │   └── loading.tsx          # Skeleton loading
    │   ├── campaigns/
    │   │   ├── page.tsx             # Список кампаний
    │   │   ├── loading.tsx
    │   │   └── [id]/
    │   │       ├── page.tsx         # Детали кампании
    │   │       └── loading.tsx
    │   ├── conversations/
    │   │   ├── page.tsx             # Split view: список + чат
    │   │   └── loading.tsx
    │   ├── leads/
    │   │   ├── page.tsx             # Таблица лидов
    │   │   └── loading.tsx
    │   └── scraper/
    │       └── page.tsx             # Кеш скраппера
    ├── components/
    │   ├── ui/                      # shadcn/ui (генерируется CLI)
    │   │   ├── button.tsx
    │   │   ├── card.tsx
    │   │   ├── badge.tsx
    │   │   ├── table.tsx
    │   │   ├── tabs.tsx
    │   │   ├── input.tsx
    │   │   ├── select.tsx
    │   │   ├── dialog.tsx
    │   │   ├── dropdown-menu.tsx
    │   │   ├── sidebar.tsx
    │   │   ├── separator.tsx
    │   │   ├── skeleton.tsx
    │   │   ├── scroll-area.tsx
    │   │   └── chart.tsx            # Recharts wrapper от shadcn
    │   ├── layout/
    │   │   ├── AppSidebar.tsx       # Sidebar: навигация по разделам
    │   │   ├── PageHeader.tsx       # Заголовок страницы + breadcrumbs
    │   │   └── ThemeProvider.tsx    # next-themes provider
    │   ├── dashboard/
    │   │   ├── StatsCards.tsx       # 5 KPI карточек (отправлено, ответили, warm, rejected, конверсия)
    │   │   ├── FunnelChart.tsx      # Горизонтальная воронка статусов
    │   │   ├── TimelineChart.tsx    # AreaChart по дням (Recharts)
    │   │   └── CampaignTable.tsx    # Мини-таблица сравнения кампаний
    │   ├── campaigns/
    │   │   ├── CampaignList.tsx     # Карточки кампаний (grid)
    │   │   ├── CampaignCard.tsx     # Одна карточка: название, статус, прогресс-бар, KPI
    │   │   ├── CampaignDetail.tsx   # Детали: оффер, промпт, даты
    │   │   └── RecipientsTable.tsx  # DataTable с фильтрами по статусу
    │   ├── conversations/
    │   │   ├── ConversationList.tsx  # Список чатов (левая панель)
    │   │   ├── ConversationItem.tsx  # Превью чата: компания, статус, последнее сообщение
    │   │   ├── ChatPanel.tsx        # Панель чата (правая часть)
    │   │   ├── ChatMessage.tsx      # Пузырь сообщения (assistant/user)
    │   │   ├── ChatHeader.tsx       # Заголовок чата: компания, телефон, статус
    │   │   └── ConversationFilters.tsx # Фильтры: статус, кампания, поиск
    │   ├── leads/
    │   │   ├── LeadsTable.tsx       # DataTable (TanStack Table)
    │   │   └── LeadStatsCards.tsx   # Статистика по категориям
    │   └── shared/
    │       ├── StatusBadge.tsx      # Бейдж статуса с цветом (warm=green, rejected=red...)
    │       ├── EmptyState.tsx       # Заглушка "нет данных"
    │       └── DataTablePagination.tsx # Переиспользуемая пагинация
    ├── hooks/
    │   ├── use-api.ts              # SWR wrapper: useFetch<T>(url, options)
    │   ├── use-websocket.ts        # WebSocket хук с reconnect
    │   ├── use-campaigns.ts        # useCampaigns(), useCampaign(id)
    │   ├── use-conversations.ts    # useConversations(filters), useChat(campaignId, phone)
    │   └── use-dashboard.ts        # useStats(), useFunnel(), useTimeline()
    ├── lib/
    │   ├── api.ts                  # API_BASE_URL, fetcher для SWR
    │   ├── types.ts                # TypeScript типы (зеркало Pydantic schemas)
    │   ├── constants.ts            # STATUS_COLORS, STATUS_LABELS, NAV_ITEMS
    │   └── utils.ts                # formatDate, formatPhone, pluralize
    └── styles/
        └── fonts.ts                # Plus Jakarta Sans (next/font/google)
```

---

## 2. API эндпоинты — Request / Response

### 2.1. Dashboard

#### `GET /api/dashboard/stats`

Общие KPI из всех кампаний.

```
Response 200:
{
  "total_campaigns": 3,
  "active_campaigns": 1,
  "total_recipients": 60,
  "total_sent": 42,
  "total_delivered": 42,          // = sent (Telegram не различает)
  "total_replied": 18,            // status in (talking, warm, warm_confirmed, referral)
  "total_warm": 4,                // warm + warm_confirmed
  "total_rejected": 8,
  "total_no_response": 6,
  "total_not_found": 10,
  "response_rate": 42.86,         // replied / sent * 100
  "conversion_rate": 9.52,        // warm / sent * 100
  "avg_messages_per_conversation": 4.2
}
```

#### `GET /api/dashboard/funnel`

Воронка по статусам (все кампании).

```
Response 200:
{
  "stages": [
    {"stage": "total",          "count": 60, "label": "Всего получателей"},
    {"stage": "sent",           "count": 42, "label": "Отправлено"},
    {"stage": "replied",        "count": 18, "label": "Ответили"},
    {"stage": "talking",        "count": 8,  "label": "В диалоге"},
    {"stage": "warm",           "count": 4,  "label": "Заинтересованы"},
    {"stage": "warm_confirmed", "count": 3,  "label": "Подтверждены"},
    {"stage": "rejected",       "count": 8,  "label": "Отказ"},
    {"stage": "no_response",    "count": 6,  "label": "Без ответа"},
    {"stage": "not_found",      "count": 10, "label": "Не в Telegram"}
  ]
}
```

#### `GET /api/dashboard/timeline?days=30&campaign_id=optional`

Динамика по дням.

```
Query params:
  days: int = 30
  campaign_id: str? = null        // фильтр по кампании

Response 200:
{
  "points": [
    {
      "date": "2026-03-15",
      "sent": 5,
      "replied": 3,
      "warm": 0,
      "rejected": 1
    },
    {
      "date": "2026-03-16",
      "sent": 9,
      "replied": 7,
      "warm": 1,
      "rejected": 2
    }
  ]
}
```

> **Примечание:** timeline строится из `last_message_at` recipients. Для `sent` — дата первого сообщения (первый элемент conversation_history). Поскольку timestamp отсутствует в conversation_history, используем `last_message_at` и `sent_count` как приблизительные метрики.

---

### 2.2. Campaigns

#### `GET /api/campaigns`

```
Query params:
  status: str? = null             // "sending", "listening", "paused", "completed"

Response 200:
{
  "campaigns": [
    {
      "campaign_id": "20260315_143022",
      "name": "Продвижение карточки на картах",
      "user_id": 590317122,
      "status": "listening",
      "recipients_total": 20,
      "sent_count": 14,
      "warm_count": 1,
      "rejected_count": 3,
      "not_found_count": 6,
      "response_rate": 71.4,
      "has_system_prompt": true,
      "has_service_info": true
    }
  ]
}
```

#### `GET /api/campaigns/{campaign_id}`

```
Response 200:
{
  "campaign_id": "20260315_143022",
  "name": "Продвижение карточки на картах",
  "user_id": 590317122,
  "status": "listening",
  "offer": "Здравствуйте, специализируемся на продвижении...",
  "system_prompt": "...",           // пусто если дефолтный
  "service_info": "...",
  "manager_ids": [590317122],
  "recipients_total": 20,
  "sent_count": 14,
  "warm_count": 1,
  "rejected_count": 3,
  "not_found_count": 6,
  "statuses_breakdown": {
    "pending": 0, "sent": 10, "talking": 0,
    "warm": 0, "warm_confirmed": 1, "rejected": 3,
    "no_response": 0, "not_found": 6, "error": 0
  }
}
```

#### `GET /api/campaigns/{campaign_id}/recipients`

```
Query params:
  status: str? = null             // "sent,talking,warm,warm_confirmed"
  search: str? = null             // поиск по company_name, contact_name
  offset: int = 0
  limit: int = 50

Response 200:
{
  "recipients": [
    {
      "phone": "+79001234567",
      "company_name": "Ресторан Пушкин",
      "contact_name": "Иван Петрович",
      "category": "Рестораны",
      "status": "warm_confirmed",
      "last_message_at": "2026-03-16T14:22:00Z",
      "messages_count": 8,
      "ping_count": 0,
      "rating": 4.5,
      "address": "Москва, ул. Тверская, 10",
      "account_phone": "+79009876543"
    }
  ],
  "total": 20,
  "offset": 0,
  "limit": 50
}
```

---

### 2.3. Conversations

#### `GET /api/conversations`

Все recipients с `len(conversation_history) > 0`, сортировка по `last_message_at DESC`.

```
Query params:
  status: str? = null             // "talking,warm,warm_confirmed"
  campaign_id: str? = null
  search: str? = null             // по company_name или тексту сообщений
  offset: int = 0
  limit: int = 50

Response 200:
{
  "conversations": [
    {
      "campaign_id": "20260315_143022",
      "phone": "+79001234567",
      "company_name": "Ресторан Пушкин",
      "contact_name": "Иван Петрович",
      "category": "Рестораны",
      "status": "warm_confirmed",
      "last_message_at": "2026-03-16T14:22:00Z",
      "messages_count": 8,
      "last_message": {
        "role": "user",
        "content": "Да, давайте созвонимся завтра"
      },
      "unread": false               // future: последнее от user и нет ответа
    }
  ],
  "total": 14,
  "offset": 0,
  "limit": 50
}
```

#### `GET /api/conversations/{campaign_id}/{phone}`

Полная переписка.

```
Response 200:
{
  "recipient": {
    "phone": "+79001234567",
    "company_name": "Ресторан Пушкин",
    "contact_name": "Иван Петрович",
    "category": "Рестораны",
    "rating": 4.5,
    "reviews_count": 128,
    "website": "pushkin-restaurant.ru",
    "address": "Москва, ул. Тверская, 10",
    "status": "warm_confirmed",
    "last_message_at": "2026-03-16T14:22:00Z",
    "ping_count": 0,
    "account_phone": "+79009876543"
  },
  "messages": [
    {"role": "assistant", "content": "Иван, здравствуйте, коротко по «Ресторан Пушкин»..."},
    {"role": "user",      "content": "Добрый день, что предлагаете?"},
    {"role": "assistant", "content": "Продвижение карточки на картах..."},
    {"role": "user",      "content": "[голосовое] да, интересно, расскажите подробнее"}
  ],
  "campaign": {
    "campaign_id": "20260315_143022",
    "name": "Продвижение карточки на картах",
    "offer": "..."
  }
}
```

> **Ограничение:** У сообщений нет индивидуальных timestamp. На фронте отображаем хронологически (по порядку массива) без времени.

---

### 2.4. Leads

#### `GET /api/leads`

Уникальные лиды (дедупликация по нормализованному телефону).

```
Query params:
  status: str? = null
  category: str? = null
  search: str? = null
  sort_by: str = "last_message_at"  // "company_name", "status"
  offset: int = 0
  limit: int = 50

Response 200:
{
  "leads": [
    {
      "phone": "+79001234567",
      "company_name": "Ресторан Пушкин",
      "contact_name": "Иван Петрович",
      "category": "Рестораны",
      "status": "warm_confirmed",    // последний статус
      "campaigns_count": 1,
      "total_messages": 8,
      "last_activity": "2026-03-16T14:22:00Z",
      "rating": 4.5,
      "address": "Москва, ул. Тверская, 10"
    }
  ],
  "total": 35,
  "offset": 0,
  "limit": 50
}
```

#### `GET /api/leads/stats`

```
Response 200:
{
  "total": 35,
  "by_status": {
    "sent": 10,
    "talking": 5,
    "warm_confirmed": 3,
    "rejected": 8,
    "no_response": 6,
    "not_found": 10,
    "referral": 1
  },
  "by_category": {
    "Рестораны": 12,
    "Автосервисы": 8,
    "Стоматологии": 5,
    "Фитнес": 10
  }
}
```

---

### 2.5. Scraper Cache

#### `GET /api/scraper/cache`

```
Response 200:
{
  "queries": [
    {
      "query": "автосервисы Москва",
      "companies_count": 200,
      "from_twogis": 120,
      "from_yandex": 115,
      "duplicates_removed": 35,
      "file_size_kb": 127.8
    }
  ]
}
```

#### `GET /api/scraper/cache/{query}`

```
Query params:
  offset: int = 0
  limit: int = 50

Response 200:
{
  "query": "автосервисы Москва",
  "companies": [
    {
      "name": "Volvo сервисный",
      "address": "Москва, ул. Ленина, 15",
      "source": "2gis",
      "phone": "+74951234567",
      "category": "Автосервис",
      "rating": 4.2,
      "reviews_count": 45,
      "inn": "7701234567",
      "website": "volvo-service.ru"
    }
  ],
  "total": 200,
  "offset": 0,
  "limit": 50
}
```

---

### 2.6. Accounts

#### `GET /api/accounts`

```
Response 200:
{
  "accounts": [
    {
      "phone_masked": "+7900***4567",    // маскированный
      "active": true,
      "session_name": "userbot_session"
    }
  ],
  "total_accounts": 1,
  "active_accounts": 1
}
```

> **Безопасность:** api_id, api_hash не возвращаются. sent_today доступен только при интеграции с живым ботом (Этап 2).

---

## 3. WebSocket события

### Endpoint

```
WS /api/ws/events?token={jwt_token}
```

### Механизм (Этап 1 — polling fallback)

На Этапе 1 WebSocket не обязателен. Вместо него SWR polling:
- Dashboard: `refreshInterval: 30000` (30 сек)
- Conversations: `refreshInterval: 10000` (10 сек)
- Campaigns: `refreshInterval: 15000` (15 сек)

### Механизм (Этап 2 — true WebSocket)

Backend: `watchdog` FileSystemEventHandler на `data/outreach/`.
При изменении JSON файла → парсинг diff → отправка events подключённым клиентам.

### Типы событий

```typescript
// Клиент → Сервер
{ "type": "subscribe", "channels": ["campaigns", "conversations"] }
{ "type": "unsubscribe", "channels": ["conversations"] }
{ "type": "ping" }

// Сервер → Клиент
{
  "type": "campaign_updated",
  "data": {
    "campaign_id": "20260315_143022",
    "status": "listening",
    "sent_count": 15,            // было 14
    "warm_count": 2              // было 1
  }
}

{
  "type": "new_message",
  "data": {
    "campaign_id": "20260315_143022",
    "phone": "+79001234567",
    "company_name": "Ресторан Пушкин",
    "message": {
      "role": "user",
      "content": "Да, давайте созвонимся"
    },
    "new_status": "warm_confirmed"
  }
}

{
  "type": "status_changed",
  "data": {
    "campaign_id": "20260315_143022",
    "phone": "+79001234567",
    "old_status": "talking",
    "new_status": "warm_confirmed"
  }
}

{
  "type": "stats_updated",
  "data": { ... }               // Сокращённый DashboardStats
}

{ "type": "pong" }
```

---

## 4. React компоненты — иерархия

```
RootLayout (layout.tsx)
├── ThemeProvider (dark mode forced)
├── SWRConfig (global fetcher)
├── AppSidebar
│   ├── Logo
│   ├── NavItem: Dashboard    (/dashboard)
│   ├── NavItem: Campaigns    (/campaigns)
│   ├── NavItem: Conversations (/conversations)
│   ├── NavItem: Leads         (/leads)
│   ├── NavItem: Scraper       (/scraper)
│   └── StatusIndicator (бот online/offline — Этап 2)
└── <main> (children)

/dashboard → DashboardPage
├── PageHeader (title="Dashboard")
├── StatsCards (5 карточек в ряд)
│   └── StatCard × 5 (icon + value + label + trend)
├── div.grid-cols-2
│   ├── TimelineChart (Recharts AreaChart)
│   │   └── ChartTooltip, ChartLegend
│   └── FunnelChart (Recharts BarChart horizontal)
│       └── FunnelBar × N stages
└── CampaignTable (мини-таблица сравнения)

/campaigns → CampaignsPage
├── PageHeader (title="Кампании")
└── CampaignList (grid)
    └── CampaignCard × N
        ├── Badge (status)
        ├── ProgressBar (sent / total)
        └── KPI row (sent, warm, rejected)

/campaigns/[id] → CampaignDetailPage
├── PageHeader (title=campaign.name, back button)
├── CampaignDetail
│   ├── Card: Оффер (текст)
│   ├── Card: Статистика (statuses_breakdown → mini chart)
│   └── Card: Настройки (system_prompt, service_info — collapsed)
├── Tabs
│   ├── Tab "Все" → RecipientsTable (all)
│   ├── Tab "В диалоге" → RecipientsTable (status=talking,warm)
│   ├── Tab "Теплые" → RecipientsTable (status=warm,warm_confirmed)
│   └── Tab "Отказы" → RecipientsTable (status=rejected)
└── RecipientsTable (TanStack DataTable)
    ├── FilterBar (search input + status select)
    ├── Table (company_name, phone, status, last_message_at, messages_count)
    │   └── Row → StatusBadge, clickable → opens conversation
    └── DataTablePagination

/conversations → ConversationsPage (SPLIT VIEW)
├── PageHeader (title="Диалоги")
└── div.flex.h-full
    ├── ConversationList (w-[400px], scrollable)
    │   ├── ConversationFilters
    │   │   ├── Input (search)
    │   │   ├── Select (status filter)
    │   │   └── Select (campaign filter)
    │   └── ScrollArea
    │       └── ConversationItem × N
    │           ├── Avatar (first letter of company)
    │           ├── company_name + contact_name
    │           ├── StatusBadge
    │           ├── last_message preview (truncated)
    │           └── last_message_at (relative: "2ч назад")
    └── ChatPanel (flex-1)
        ├── ChatHeader
        │   ├── company_name, contact_name, phone
        │   ├── StatusBadge (large)
        │   └── Info button → Sheet with recipient details
        ├── ScrollArea (messages)
        │   └── ChatMessage × N
        │       ├── if role=assistant → left aligned, muted bg
        │       └── if role=user → right aligned, accent bg
        └── EmptyState (если чат не выбран)

/leads → LeadsPage
├── PageHeader (title="Лиды")
├── LeadStatsCards (by_status mini-cards)
└── LeadsTable (TanStack DataTable)
    ├── FilterBar (search, status select, category select)
    ├── Table (company, phone, category, status, messages, last_activity)
    └── DataTablePagination

/scraper → ScraperPage
├── PageHeader (title="Скраппер — кеш")
└── Table (query, companies_count, sources breakdown)
    └── Row clickable → expand with companies list
```

### Компоненты shadcn/ui для установки

```bash
npx shadcn@latest init
npx shadcn@latest add button card badge input select tabs table \
  dialog sheet dropdown-menu separator skeleton scroll-area \
  sidebar chart tooltip avatar
```

### Дополнительные библиотеки

```
swr                    — data fetching + polling
recharts               — графики (уже интегрирован в shadcn chart)
@tanstack/react-table  — DataTable
lucide-react           — иконки (уже в shadcn)
date-fns               — форматирование дат
```

---

## 5. Порядок реализации

### Шаг 0: Инфраструктура (фундамент)

**Backend:**
- [ ] Инициализация FastAPI проекта (`web/backend/`)
- [ ] `core/config.py` — Settings с путями к данным
- [ ] `services/data_reader.py` — DataReader: чтение + парсинг JSON, кеш по file mtime
- [ ] CORS middleware (localhost:3000)
- [ ] Pydantic schemas в `api/schemas/`

**Frontend:**
- [ ] `npx create-next-app` с TypeScript + Tailwind + App Router
- [ ] shadcn/ui init + установка базовых компонентов
- [ ] Настройка шрифта Plus Jakarta Sans
- [ ] `globals.css` — тёмная палитра (#0a0a0f, #111118, accent emerald)
- [ ] `layout.tsx` — RootLayout + AppSidebar (статичный)
- [ ] `lib/api.ts` — fetcher, API_BASE_URL
- [ ] `lib/types.ts` — TypeScript типы

**Проверка:** FastAPI отдаёт JSON на `/api/health`, Next.js показывает sidebar с заглушками.

---

### Шаг 1: Дашборд

**Backend:**
- [ ] `routes/dashboard.py` — 3 эндпоинта (stats, funnel, timeline)
- [ ] `services/stats.py` — агрегация из DataReader

**Frontend:**
- [ ] `hooks/use-dashboard.ts` — SWR хуки
- [ ] `StatsCards.tsx` — 5 KPI карточек с glass-morphism
- [ ] `FunnelChart.tsx` — горизонтальная воронка (Recharts BarChart)
- [ ] `TimelineChart.tsx` — AreaChart по дням
- [ ] `dashboard/page.tsx` — сборка

**Проверка:** Дашборд показывает реальные данные из кампании.

---

### Шаг 2: Кампании

**Backend:**
- [ ] `routes/campaigns.py` — список, детали, recipients

**Frontend:**
- [ ] `CampaignList.tsx` + `CampaignCard.tsx`
- [ ] `CampaignDetail.tsx` — оффер, настройки
- [ ] `RecipientsTable.tsx` — DataTable с фильтрами и пагинацией
- [ ] `StatusBadge.tsx` — universal component
- [ ] `campaigns/page.tsx` + `campaigns/[id]/page.tsx`

**Проверка:** Можно просмотреть кампанию и все recipients с фильтрацией.

---

### Шаг 3: Чаты (самая сложная часть)

**Backend:**
- [ ] `routes/conversations.py` — список + полная переписка
- [ ] Поиск по тексту сообщений (фильтрация в DataReader)

**Frontend:**
- [ ] `ConversationList.tsx` + `ConversationItem.tsx`
- [ ] `ConversationFilters.tsx`
- [ ] `ChatPanel.tsx` + `ChatMessage.tsx` + `ChatHeader.tsx`
- [ ] Split view layout (responsive: на mobile — только список или чат)
- [ ] Auto-scroll к последнему сообщению
- [ ] `conversations/page.tsx`
- [ ] SWR polling `refreshInterval: 10000` для quasi-realtime

**Проверка:** Можно выбрать чат из списка и просмотреть всю переписку.

---

### Шаг 4: Лиды

**Backend:**
- [ ] `routes/leads.py` — список + статистика

**Frontend:**
- [ ] `LeadsTable.tsx` — DataTable с сортировкой, фильтрами
- [ ] `LeadStatsCards.tsx`
- [ ] `leads/page.tsx`

**Проверка:** Таблица всех уникальных лидов с фильтрацией.

---

### Шаг 5: Скраппер + аккаунты

**Backend:**
- [ ] `routes/scraper.py` — кеш
- [ ] `routes/accounts.py` — список (маскированный)

**Frontend:**
- [ ] `scraper/page.tsx` — таблица + expandable rows
- [ ] (Аккаунты — виджет на дашборде или отдельная страница)

---

### Шаг 6: Polish

- [ ] Loading skeletons для всех страниц
- [ ] Empty states с иллюстрациями
- [ ] Staggered fade-in анимации (framer-motion)
- [ ] Responsive: sidebar collapse на tablet
- [ ] Error boundaries
- [ ] Meta tags / page titles

---

### Шаг 7: WebSocket (Этап 2 — после одобрения)

**Backend:**
- [ ] `services/ws_manager.py` — ConnectionManager
- [ ] File watcher (watchdog) на `data/outreach/`
- [ ] Diff detection: сравнение old/new JSON при изменении файла
- [ ] `routes/ws.py` — WebSocket endpoint

**Frontend:**
- [ ] `hooks/use-websocket.ts` — с reconnect и event dispatch
- [ ] Обновление SWR cache при получении WS events
- [ ] Notification toast при new_message / status_changed
