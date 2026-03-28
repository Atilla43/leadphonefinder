# Signal Grid — Дизайн-концепция веб-платформы

## 1. Визуальная идентичность

### Название стиля: **Signal Grid**

### Метафора
Платформа — это **центр управления сигналами**. Твои боты — автономные агенты в поле, рассылающие сообщения. Каждый ответ лида — это сигнал, вернувшийся на радар. Дашборд — экран оператора, который наблюдает как сигналы проходят через воронку: шум (нет ответа) → слабый сигнал (talking) → сильный сигнал (warm) → подтверждённый контакт (warm_confirmed).

### Mood
**Контроль. Точность. Спокойная уверенность.**

Интерфейс должен вызывать ощущение, что ты держишь руку на пульсе работающей системы. Не игрушка, не развлечение — профессиональный инструмент для заработка денег. Как приборная панель Tesla, не как приложение для заметок.

### Ключевая дизайн-идея
**Dot Grid Background + Signal Pulse**

Фон основной контентной области имеет едва заметную точечную сетку (как миллиметровка или экран радара). Точки — `#ffffff08` на `#08090d` фоне, шаг 24px. Это создаёт:
1. Ощущение структуры и порядка без видимых линий
2. Связь с метафорой "Grid" — данные организованы в сетку
3. Визуальный якорь, который не мешает контенту

При получении WebSocket-события (новое сообщение, смена статуса) обновлённая карточка кратко мигает emerald-бордером. В будущем (v2) — pulse-рябь распространяется по точкам сетки от элемента наружу.

### Почему это запоминается
| Типичный дашборд | Signal Grid |
|---|---|
| Синий/фиолетовый акцент | Emerald — деньги, рост, ночное видение |
| Inter/Roboto | Geist Sans + Geist Mono (числа как показания приборов) |
| Плоский серый фон | Dot grid — структура без шума |
| Статичные бейджи | Ping-dot индикаторы — система «живёт» |
| Одинаковые тени | Emerald glow на hover/active — цветной свет |

### Референсы
- **Linear** — за минимализм и сдержанность в использовании цвета
- **Vercel** — за чёрные фоны и "инженерную" эстетику
- **Resend** — за дисциплину одного акцентного цвета
- **Не PostHog** — без иронии и "fun", это серьёзный инструмент

---

## 2. Палитра

### Фоны
| Роль | Hex | Где используется |
|------|-----|------------------|
| Base | `#08090d` | Фон страницы, основной контент |
| Surface 1 | `#0f1117` | Карточки, модальные окна |
| Surface 2 | `#0c0d12` | Sidebar |
| Surface 3 | `#161822` | Hover-состояния, выделенные строки |
| Elevated | `#1a1c2a` | Dropdown-меню, tooltips |

### Бордеры
| Роль | Hex | Где используется |
|------|-----|------------------|
| Default | `#1e2030` | Границы карточек, разделители |
| Hover | `#2a2d42` | При наведении на карточки |
| Focus | `#10b981` | Фокус на input, active sidebar item |

### Акцент — Emerald
| Вариация | Hex | Где используется |
|----------|-----|------------------|
| Primary | `#10b981` | Кнопки CTA, активные элементы, ссылки |
| Bright | `#34d399` | Выделение, hover на кнопках |
| Muted | `#065f46` | Фон бейджей "success", muted backgrounds |
| Glow | `#10b98133` | box-shadow для emerald glow эффекта |
| Subtle BG | `#10b98110` | Фон правых пузырей чата (бот) |

### Вторичный — Cyan (только для графиков и info-бейджей)
| Вариация | Hex | Использование |
|----------|-----|---------------|
| Primary | `#06b6d4` | Вторая серия на графиках, info-бейджи |
| Muted | `#164e63` | Фон info-бейджей |

### Статусные цвета
| Статус | Цвет | Hex | Маппинг на данные |
|--------|------|-----|-------------------|
| Success | Emerald | `#10b981` | warm, warm_confirmed |
| Warning | Amber | `#f59e0b` | sent (ждём ответа), pending |
| Error | Rose | `#f43f5e` | rejected, error |
| Info | Cyan | `#06b6d4` | talking, referral |
| Neutral | Gray | `#6b7280` | not_found, no_response |

### Текст
| Роль | Hex | Использование |
|------|-----|---------------|
| Primary | `#f1f5f9` | Заголовки, основной текст |
| Secondary | `#94a3b8` | Описания, вторичная информация |
| Muted | `#475569` | Плейсхолдеры, неактивные элементы |
| Inverted | `#08090d` | Текст на светлых кнопках |

---

## 3. Типографика

### Шрифт: **Geist Sans + Geist Mono**

**Почему Geist:**
- Создан Vercel специально для UI — оптимизирован для экранного чтения при любом размере
- Geist Mono идеален для чисел и метрик — даёт ощущение "показания прибора"
- Пара Sans + Mono создаёт контраст "человеческое описание + точное измерение"
- Доступен через `next/font` с автоматической оптимизацией
- Не перегружен в экосистеме (в отличие от Inter в каждом shadcn-проекте)

**Почему НЕ Inter:** дефолт shadcn/ui. Мгновенно делает любой дашборд "шаблонным".
**Почему НЕ Roboto:** ассоциация с Material Design/Android. Слишком generic.
**Почему НЕ Plus Jakarta Sans:** хорош, но слишком "тёплый" и "дружелюбный" для инструмента контроля.

### Type Scale

| Роль | Шрифт | Размер | Weight | Tracking | Пример |
|------|-------|--------|--------|----------|--------|
| Page title (h1) | Geist Sans | 28px | 600 (semibold) | -0.02em | "Аналитика" |
| Section title (h2) | Geist Sans | 20px | 600 (semibold) | -0.01em | "Воронка продаж" |
| Card title (h3) | Geist Sans | 14px | 500 (medium) | 0 | "Отправлено" |
| Body text | Geist Sans | 14px | 400 (regular) | 0 | Описания, сообщения |
| Small/caption | Geist Sans | 12px | 400 (regular) | 0.01em | Timestamps, подписи |
| **Stat numbers** | **Geist Mono** | **32px** | **700 (bold)** | **-0.02em** | **"1,247"** |
| Table data | Geist Mono | 13px | 400 (regular) | 0 | Числа в таблицах |
| Badge text | Geist Sans | 11px | 500 (medium) | 0.02em | "WARM", "SENT" |
| Input text | Geist Sans | 14px | 400 (regular) | 0 | Поля ввода |

> **Ключевое правило:** Все числа и метрики — в Geist Mono. Все описательные тексты — в Geist Sans. Это создаёт визуальное разделение между "данными" и "интерфейсом".

---

## 4. Компоненты

### 4.1 Layout Shell — Sidebar + Header + Content

**Источник:** Паттерн "Dashboard with Collapsible Sidebar" из 21st.dev (адаптирован).

**Реализация:** Кастомный. Берём структуру (collapsible sidebar с иконками), но полностью переписываем стили под Signal Grid.

| Элемент | Описание |
|---------|----------|
| Sidebar | Фиксирован слева. Ширина: 240px expanded / 64px collapsed. Фон: `#0c0d12`. Нижний бордер-right: 1px `#1e2030` |
| Nav items | Иконка (lucide-react) + текст. Active: left-border 2px emerald + фон `#10b98110` + текст `#10b981`. Hover: фон `#161822` |
| Logo | Верх sidebar. Emerald иконка/знак (стилизованная "S" или стрелка-сигнал) + "Signal Grid" текст |
| Content | Справа от sidebar. Фон: `#08090d` с dot grid pattern (background-image radial-gradient) |
| Header | Внутри content area, не глобальный. Page title (h1) + breadcrumbs. Нет отдельной "шапки" — чистый минимализм |

**Dot Grid CSS:**
```css
background-image: radial-gradient(circle, #ffffff08 1px, transparent 1px);
background-size: 24px 24px;
```

### 4.2 KPI-карточки (Stat Cards)

**Источник:** Гибрид из 21st.dev:
- Анимация чисел через `framer-motion useSpring` (из компонента "Card" card-10)
- Мини area chart (sparkline) из "Stats cards with area chart"

**Реализация:**

```
┌─────────────────────────────┐
│ ↗ icon          Отправлено  │  ← Card title (Geist Sans 14px, muted)
│                             │
│         1,247               │  ← Stat number (Geist Mono 32px bold, primary)
│     +12.5% ▲                │  ← Trend (Geist Sans 12px, emerald/rose)
│                             │
│ ▁▂▃▅▃▄▆▅▇█                 │  ← Mini sparkline (emerald, 40px height)
└─────────────────────────────┘
```

| Свойство | Значение |
|----------|----------|
| Фон | `#0f1117` |
| Бордер | 1px `#1e2030` |
| Border-radius | 12px |
| Hover | border → `#2a2d42`, box-shadow: `0 0 20px #10b98110` |
| Padding | 24px |
| Число | Анимация от 0 до значения при mount (spring, 1.5s) |
| Sparkline | Recharts AreaChart, high: `#10b981`, gradient fill to transparent |

### 4.3 Графики

**Источник:** shadcn/ui Chart wrapper + Recharts. Паттерн ChartContainer из 21st.dev "Stats cards with area chart".

**Timeline (Area Chart):**
- Две серии: Sent (emerald) и Responses (cyan)
- Gradient fill: color → transparent сверху вниз
- Grid lines: `#1e2030`, dashed
- Axis text: Geist Mono 12px, `#475569`
- Tooltip: dark card (#0f1117) с emerald border

**Funnel (Horizontal Bars):**
- Кастомный (не Recharts). Горизонтальные бары с анимацией ширины.
- Каждый этап: label (Geist Sans) | bar (gradual emerald-to-muted) | count (Geist Mono)
- Бары анимируются слева направо при mount (staggerChildren: 0.1)

### 4.4 Data Table

**Источник:** shadcn/ui Table + TanStack Table v8.

**Стилизация:**
| Элемент | Стиль |
|---------|-------|
| Header row | Фон: `#0c0d12`, текст: `#94a3b8` uppercase 11px, letter-spacing 0.05em |
| Body row | Фон: transparent. Hover: `#161822` |
| Selected row | Left-border 2px emerald, фон `#10b98110` |
| Borders | Только горизонтальные: 1px `#1e2030`. Без вертикальных |
| Pagination | Внизу, compact. "1-20 of 47" + prev/next buttons |
| Sorting | Иконка arrow-up/down в header. Active sort: emerald icon |

### 4.5 Chat Interface

**Источник:** Кастомный (21st.dev ChatComponent слишком generic для Telegram-специфики).

**Layout:** Split panel — список слева (350px fixed) + чат справа (flex).

**Список диалогов:**
```
┌──────────────────────────────────┐
│ 🔍 Поиск...                     │
│ [All] [Active] [Warm] [Rejected] │
├──────────────────────────────────┤
│ ● ООО "Ромашка"         14:23  │  ← emerald dot = active
│   Да, расскажите подробн...      │
├──────────────────────────────────┤
│ ○ ИП Иванов              вчера  │  ← gray dot = no_response
│   Нет, спасибо                   │
├──────────────────────────────────┤
│ ...                              │
└──────────────────────────────────┘
```

| Элемент | Стиль |
|---------|-------|
| Card | padding 12px, hover: `#161822`, active: emerald left-border 2px |
| Company name | Geist Sans 14px medium, `#f1f5f9` |
| Last message | Geist Sans 13px, `#475569`, truncated 1 line |
| Timestamp | Geist Mono 11px, `#475569`, right-aligned |
| Status dot | 8px circle с ping-анимацией для active statuses |

**Окно чата:**
```
┌──────────────────────────────────────────┐
│ ООО "Ромашка" · Иван Петров · 🟢 talking │
│ Кампания: "Рестораны Сочи"               │
├──────────────────────────────────────────┤
│                                          │
│  ┌─ Bot ─────────────────────┐           │
│  │ Здравствуйте! Мы предла...│           │  ← правый bubble, emerald muted bg
│  │                     AI 🤖 │           │
│  └───────────────────────────┘           │
│                                          │
│        ┌─ Lead ──────────┐               │
│        │ А что за услуга? │               │  ← левый bubble, surface 3 bg
│        └─────────────────┘               │
│                                          │
│  ┌─ Bot ─────────────────────┐           │
│  │ Мы помогаем привлекать... │           │
│  │                     AI 🤖 │           │
│  └───────────────────────────┘           │
│                                          │
└──────────────────────────────────────────┘
```

| Элемент | Стиль |
|---------|-------|
| Bot bubble | bg: `#10b98110`, border: 1px `#10b98130`, border-radius: 12px 12px 4px 12px |
| Lead bubble | bg: `#161822`, border: 1px `#1e2030`, border-radius: 12px 12px 12px 4px |
| AI badge | Geist Sans 10px, `#10b981`, внутри бота-пузыря |
| Day separator | "— 25 марта —" центрированный, Geist Sans 11px, `#475569` |
| Message text | Geist Sans 14px, `#f1f5f9` |

### 4.6 Campaign Cards

**Реализация:** Кастомный.

```
┌─────────────────────────────────┐
│ Рестораны Сочи     🟢 listening │
│                                 │
│  Sent   Warm   Rejected         │
│   14      1       3             │  ← Geist Mono, цветные
│                                 │
│ ████████████░░░░ 70%            │  ← progress bar
│                                 │
│ 25 мар 2026        Подробнее → │
└─────────────────────────────────┘
```

| Свойство | Значение |
|----------|----------|
| Фон | `#0f1117` |
| Бордер | 1px `#1e2030`, hover: `#2a2d42` |
| Border-radius | 12px |
| Hover | y: -2 (framer-motion), box-shadow: `0 4px 20px #00000040` |
| Progress bar | Фон: `#1e2030`, заполнение: emerald gradient |
| Status badge | С ping-dot для active (listening, sending) |

### 4.7 Status Badges

**Источник:** Компонент "Status" из 21st.dev с ping-dot анимацией.

**Маппинг статусов:**

| Статус recipient | Badge | Ping | Цвет |
|-----------------|-------|------|------|
| pending | Pending | нет | amber muted |
| sent | Sent | нет | amber |
| talking | Talking | **да** | cyan |
| warm | Warm | **да** | emerald |
| warm_confirmed | Confirmed | **да** | emerald bright |
| rejected | Rejected | нет | rose |
| referral | Referral | **да** | cyan |
| no_response | No response | нет | gray |
| not_found | Not found | нет | gray muted |
| error | Error | нет | rose |

| Статус кампании | Badge | Ping |
|----------------|-------|------|
| pending | Pending | нет |
| sending | Sending | **да** (emerald) |
| listening | Listening | **да** (cyan) |
| paused | Paused | нет |
| completed | Completed | нет |
| cancelled | Cancelled | нет |

**Ping CSS:**
```css
@keyframes ping {
  75%, 100% { transform: scale(2); opacity: 0; }
}
.ping-dot::before {
  animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
}
```

### 4.8 Forms и Filters

**Источник:** shadcn/ui Input, Select, Tabs.

| Элемент | Стиль |
|---------|-------|
| Input | bg: `#0f1117`, border: 1px `#1e2030`, focus: border `#10b981` + glow |
| Select | Тот же стиль. Dropdown: bg `#1a1c2a`, items hover `#161822` |
| Tabs (фильтры) | Ghost-style. Active tab: emerald text + bottom border 2px |
| Search | Input + magnifying glass icon. Placeholder: `#475569` |

### 4.9 Empty States

Для каждой страницы — минималистичный SVG + текст + CTA:

| Страница | Текст | CTA |
|----------|-------|-----|
| Dashboard (нет данных) | "Нет данных для отображения" | "Данные появятся после запуска первой кампании" |
| Conversations (нет выбора) | "Выберите диалог" | Arrow-left icon |
| Conversations (пусто) | "Нет диалогов" | "Запустите кампанию, чтобы начать" |
| Campaigns (пусто) | "Нет кампаний" | "Кампании создаются через Telegram-бота" |

SVG-иллюстрации: простые line-art в `#1e2030` с одним emerald акцентом. Не Lottie, не фото — чистые линии.

---

## 5. Анимации и микровзаимодействия

### Стратегия: **Минимум, но каждая — со смыслом**

### Критичные анимации (MVP)

| Анимация | Техника | Параметры | Зачем |
|----------|---------|-----------|-------|
| Stat count-up | `framer-motion useSpring` | damping: 100, stiffness: 100, ~1.5s | Числа "оживают", а не просто появляются |
| List stagger | `staggerChildren` | delay: 0.05s, opacity 0→1, y: 10→0 | Элементы "приходят" последовательно |
| Page transition | `AnimatePresence mode="wait"` | opacity 0→1, duration: 0.2s | Плавная смена страниц |
| Chart animation | Recharts `animationDuration` | 800ms, ease-out | Графики "рисуются" |
| Funnel bars | `staggerChildren` + width animation | stagger: 0.1, width 0%→N%, spring | Воронка раскрывается поэтапно |

### Полировочные анимации (post-MVP)

| Анимация | Техника | Когда |
|----------|---------|-------|
| Card hover lift | `whileHover: { y: -2 }` | При наведении на карточку |
| Badge ping dot | CSS `@keyframes ping` | Для активных статусов (постоянно) |
| New message slide | `initial: { opacity: 0, x: 20 }` | WebSocket: новое сообщение |
| Sidebar collapse | `layout` prop + `layoutId` | Toggle sidebar |
| Border glow pulse | CSS transition on border-color | WebSocket: данные обновились |

### НЕ делаем (осознанное ограничение)

- Параллакс скроллинг
- 3D трансформации карточек
- Particle эффекты
- Постоянные фоновые анимации (убивают battery)
- Shimmer-градиенты для скелетонов (вместо этого — opacity pulse, более сдержанно)

### Loading States

| Состояние | Подход |
|-----------|--------|
| Первая загрузка | Skeleton с opacity pulse (не shimmer) |
| Обновление данных | Stale data видны, маленький spinner в углу |
| Ошибка | Красный бейдж-toast в правом нижнем углу |

---

## 6. Новые страницы: Лендинг + Авторизация

### 6.0 Landing Page (`/`) — публичная

**Цель:** Произвести впечатление на инвесторов. Показать мощь продукта одним взглядом.

**Дизайн:** Тот же Signal Grid, но в "маркетинговом" режиме — крупнее типографика, больше воздуха, анимации при скролле.

**Секции:**

```
┌──────────────────────────────────────────────────────────┐
│ [Logo Signal Grid]          Features  Pricing   [Войти]  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│         Автоматические продажи                           │
│           через Telegram                                 │  ← Hero
│                                                          │
│   AI-бот ведёт диалоги с ЛПР, пока вы занимаетесь      │
│                    бизнесом                               │
│                                                          │
│    [Начать бесплатно]    [Смотреть демо]                 │
│                                                          │
│   ┌────────────────────────────────────────────┐         │
│   │  ╔═══ Animated Dashboard Preview ═══╗      │         │  ← Mock dashboard
│   │  ║  Sent: 1,247  Warm: 89  Conv: 7% ║      │         │     в browser frame
│   │  ║  ▁▂▃▅▃▄▆▅▇█                     ║      │         │
│   │  ╚══════════════════════════════════╝      │         │
│   └────────────────────────────────────────────┘         │
│                                                          │
│  +1,247 сообщений    12% конверсия    24/7 без перерыва  │  ← Floating badges
│                                                          │
├──────────────────────────────────────────────────────────┤
│                     Возможности                          │  ← Features
│                                                          │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│ │ 🤖       │ │ 📊       │ │ 🔄       │ │ 🎯       │    │
│ │AI-диалоги│ │Аналитика │ │Мульти-акк│ │Скраппинг │    │
│ │GPT ведёт │ │Воронка,  │ │Пул акк-в │ │Яндекс +  │    │
│ │разговоры │ │real-time │ │ротация   │ │2ГИС авто │    │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
│                                                          │
├──────────────────────────────────────────────────────────┤
│               Как это работает                           │  ← How it works
│                                                          │
│   ① Загрузите базу  ──→  ② Настройте AI  ──→  ③ Profit │
│   Скраппер соберёт      Промпт, тон,         Бот сам   │
│   контакты за вас       расписание            продаёт   │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                     Тарифы                               │  ← Pricing
│                                                          │
│  ┌──────────┐  ┌───────────────┐  ┌──────────┐         │
│  │ Starter  │  │ ★ Pro         │  │Enterprise│         │
│  │          │  │               │  │          │         │
│  │ 100 msg  │  │ 1,000 msg    │  │ Безлимит │         │
│  │ 1 аккаунт│  │ 3 аккаунта   │  │ 10 акк-в │         │
│  │          │  │               │  │ + API    │         │
│  │ Бесплатно│  │ 4,990₽/мес   │  │14,990₽/м │         │
│  │          │  │               │  │          │         │
│  │ [Начать] │  │ [Выбрать]    │  │[Связаться│         │
│  └──────────┘  └───────────────┘  └──────────┘         │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  Signal Grid · 2026          Войти · Telegram · Email    │  ← Footer
└──────────────────────────────────────────────────────────┘
```

**Компоненты лендинга:**
| Компонент | Описание | Анимация |
|-----------|----------|----------|
| `navbar.tsx` | Sticky nav: logo + links + CTA "Войти". Blur-backdrop при скролле | — |
| `hero.tsx` | Headline с gradient text, два CTA, animated dashboard mockup | fade-in + count-up чисел |
| `features.tsx` | 4 glass-morphism карточки в grid | stagger reveal при скролле |
| `how-it-works.tsx` | 3 шага, соединённых линией | step-by-step reveal |
| `pricing.tsx` | 3 тарифных карточки, Pro выделена emerald бордером | hover lift |
| `footer.tsx` | Минимальный: logo, копирайт, ссылки | — |

**Мок-дашборд в Hero:** НЕ скриншот, а живой React-компонент с анимированными числами и mini-chart. Обёрнут в стилизованную "рамку браузера" с точками светофора. Создаёт WOW-эффект.

### 6.0.1 Login (`/login`) — публичная

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│                    dot grid background                   │
│                                                          │
│              ┌─────────────────────────┐                 │
│              │     ◆ Signal Grid       │                 │
│              │                         │                 │
│              │  Email                  │                 │
│              │  ┌───────────────────┐  │                 │
│              │  │ admin@signal.grid │  │                 │
│              │  └───────────────────┘  │                 │
│              │                         │                 │
│              │  Пароль                 │                 │
│              │  ┌───────────────────┐  │                 │
│              │  │ ●●●●●●●●          │  │                 │
│              │  └───────────────────┘  │                 │
│              │                         │                 │
│              │  [      Войти       ]   │                 │
│              │                         │                 │
│              └─────────────────────────┘                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

- Карточка по центру, glass-morphism стиль (bg `#0f1117`, border `#1e2030`)
- Dot grid на фоне всей страницы
- Emerald кнопка "Войти"
- Ошибка — красный текст под формой, shake-анимация карточки
- MVP: credentials из `.env` (ADMIN_EMAIL + ADMIN_PASSWORD)

### 6.0.2 Авторизация — техническая схема

**Backend (FastAPI):**
- `POST /api/auth/login` — принимает `{email, password}`, возвращает `{access_token, token_type}`
- JWT с exp 24 часа, secret из `JWT_SECRET` env
- Middleware: все `/api/*` (кроме `/api/auth/login`, `/api/health`) требуют `Authorization: Bearer <token>`
- Credentials: `ADMIN_EMAIL` + `ADMIN_PASSWORD` в `.env`

**Frontend (Next.js):**
- Token хранится в `localStorage` + `cookie` (для middleware)
- `middleware.ts` на уровне Next.js: проверяет cookie, redirect на `/login` если нет
- API client автоматически добавляет `Authorization` header
- `/login` redirect на `/dashboard` если уже залогинен

**Route groups:**
```
src/app/
├── page.tsx                    # Landing (public)
├── (auth)/
│   ├── layout.tsx              # Centered layout, no sidebar
│   └── login/page.tsx          # Login form
├── (app)/
│   ├── layout.tsx              # Shell: sidebar + content
│   ├── dashboard/page.tsx      # Protected
│   ├── conversations/...       # Protected
│   ├── campaigns/...           # Protected
│   └── settings/page.tsx       # Protected
└── middleware.ts               # Auth guard for (app) routes
```

---

### 6.1 Dashboard (`/dashboard`)

**API:** `GET /api/dashboard/stats`, `GET /api/dashboard/funnel`, `GET /api/dashboard/timeline`

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  Аналитика                                     │
│         │                                                 │
│ ◆ Dash  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐              │
│ ○ Chats │  │Sent │ │Resp.│ │Warm │ │Conv%│  ← KPI strip  │
│ ○ Camp. │  │ 14  │ │ 10  │ │  1  │ │7.1% │              │
│ ○ Sett. │  │ ▁▃▅ │ │ ▂▄▆ │ │ ▁▂▃ │ │ ▁▂▃ │              │
│         │  └─────┘ └─────┘ └─────┘ └─────┘              │
│         │                                                 │
│         │  ┌───────────────────────┐ ┌────────────┐      │
│         │  │ Timeline Chart        │ │ Funnel     │      │
│         │  │ (area, 2 series)     │ │ pending: █ │      │
│         │  │                      │ │ sent:    █ │      │
│         │  │  ╱╲    ╱╲           │ │ talking: █ │      │
│         │  │ ╱  ╲╱╱  ╲          │ │ warm:    █ │      │
│         │  └───────────────────────┘ └────────────┘      │
│         │                                                 │
│         │  ┌─────────────────────────────────────┐       │
│         │  │ Campaigns Overview Table            │       │
│         │  │ Name | Status | Sent | Warm | Conv% │       │
│         │  │ ──────────────────────────────────── │       │
│         │  │ Рестораны Сочи | 🟢 | 14 | 1 | 7.1%│       │
│         │  └─────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

**Grid:** KPI — 4 колонки. Charts — 2:1. Table — full width.

### 6.2 Conversations (`/conversations`)

**API:** `GET /api/conversations`, `GET /api/conversations/{campaign_id}/{phone}`

```
┌──────────────────────────────────────────────────────────┐
│ SIDEBAR │ Диалоги                                         │
│         │                                                  │
│         │ ┌─────────────────┬──────────────────────────┐  │
│         │ │ 🔍 Поиск...     │ ООО "Ромашка"    🟢 talk│  │
│         │ │ All|Active|Warm  │ Кампания: Рест. Сочи    │  │
│         │ │─────────────────│──────────────────────────│  │
│         │ │● Ромашка   14:23│                          │  │
│         │ │  Да, расскаж... │    ┌─────────────────┐   │  │
│         │ │─────────────────│    │Здравствуйте! 🤖│   │  │
│         │ │○ Иванов   вчера │    └─────────────────┘   │  │
│         │ │  Нет, спасибо   │                          │  │
│         │ │─────────────────│  ┌──────────────┐        │  │
│         │ │● Петров   12:05 │  │А что за услуга?│       │  │
│         │ │  Интересно...   │  └──────────────┘        │  │
│         │ │                 │                          │  │
│         │ │                 │    ┌─────────────────┐   │  │
│         │ │                 │    │Мы помогаем... 🤖│   │  │
│         │ │                 │    └─────────────────┘   │  │
│         │ └─────────────────┴──────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**Split:** 350px fixed left panel + flex right panel.

### 6.3 Campaigns (`/campaigns`)

**API:** `GET /api/campaigns`

```
┌──────────────────────────────────────────────────────────┐
│ SIDEBAR │ Кампании                                        │
│         │                                                  │
│         │ ┌──────────────────┐ ┌──────────────────┐       │
│         │ │ Рестораны Сочи   │ │ Кафе Москва      │       │
│         │ │ 🟢 listening      │ │ ⏸ paused          │       │
│         │ │                  │ │                  │       │
│         │ │ Sent  Warm  Rej  │ │ Sent  Warm  Rej  │       │
│         │ │  14    1     3   │ │   8    0     2   │       │
│         │ │                  │ │                  │       │
│         │ │ ████████░░ 70%   │ │ ████░░░░░ 40%   │       │
│         │ │                  │ │                  │       │
│         │ │ 25 мар   →       │ │ 20 мар   →       │       │
│         │ └──────────────────┘ └──────────────────┘       │
│         │                                                  │
│         │ ┌──────────────────┐                             │
│         │ │ Барберы Питер    │                             │
│         │ │ ✓ completed      │                             │
│         │ │ ...              │                             │
│         │ └──────────────────┘                             │
└──────────────────────────────────────────────────────────┘
```

**Grid:** responsive 1→2→3 колонки. Cards animate in with stagger.

### 6.4 Campaign Detail (`/campaigns/[id]`)

**API:** `GET /api/campaigns/{id}`, `GET /api/campaigns/{id}/recipients`

```
┌──────────────────────────────────────────────────────────┐
│ SIDEBAR │ ← Кампании / Рестораны Сочи     🟢 listening    │
│         │                                                  │
│         │ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐               │
│         │ │Total│ │Sent │ │Warm │ │N/F  │ ← Stats strip  │
│         │ │ 20  │ │ 14  │ │  1  │ │  6  │               │
│         │ └─────┘ └─────┘ └─────┘ └─────┘               │
│         │                                                  │
│         │ ┌──────────────────────────────────────────┐    │
│         │ │ Recipients                               │    │
│         │ │ [All ▾] [Search...                     ] │    │
│         │ │──────────────────────────────────────────│    │
│         │ │ Company    | Contact | Status  | Msgs   │    │
│         │ │ Ромашка    | Иванов  | 🟢 talk | 4      │    │
│         │ │ Лютик      | Петров  | ❌ rej  | 2      │    │
│         │ │ Василёк    | Сидоров | ⏳ sent | 1      │    │
│         │ │ ...                                      │    │
│         │ └──────────────────────────────────────────┘    │
│         │                                                  │
│         │ ┌──────────────────────────────────────────┐    │
│         │ │ Status Distribution                      │    │
│         │ │ sent ████████████ 10                     │    │
│         │ │ rejected ██████ 3                        │    │
│         │ │ warm_confirmed ██ 1                      │    │
│         │ │ not_found ████████████ 6                 │    │
│         │ └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### 6.5 Settings (`/settings`)

**API:** `GET /api/accounts`, `GET /api/health`

```
┌──────────────────────────────────────────────────────────┐
│ SIDEBAR │ Настройки                                       │
│         │                                                  │
│         │ Bot Status                                       │
│         │ ┌──────────────────────────────────────┐        │
│         │ │ API: 🟢 Connected                    │        │
│         │ │ Outreach dir: ✓ exists               │        │
│         │ │ Cache dir: ✓ exists                   │        │
│         │ │ WebSocket: 1 connection               │        │
│         │ └──────────────────────────────────────┘        │
│         │                                                  │
│         │ Accounts                                         │
│         │ ┌──────────────────────────────────────┐        │
│         │ │ +7 (999) ***-**-01  | Active | 12/30 │        │
│         │ │ +7 (999) ***-**-02  | Active |  8/30 │        │
│         │ └──────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────┘
```

---

## 7. Файловая структура фронтенда

```
web/frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── app/                              # Next.js App Router
│   │   ├── layout.tsx                    # Root: fonts, metadata (NO shell)
│   │   ├── page.tsx                      # Landing page (public)
│   │   │
│   │   ├── (auth)/                       # Auth route group (public)
│   │   │   ├── layout.tsx                # Centered card layout
│   │   │   └── login/
│   │   │       └── page.tsx              # Login form
│   │   │
│   │   ├── (app)/                        # App route group (protected)
│   │   │   ├── layout.tsx                # Shell: sidebar + content + dot grid
│   │   │   ├── dashboard/
│   │   │   │   ├── page.tsx
│   │   │   │   └── loading.tsx
│   │   │   ├── conversations/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [campaignId]/
│   │   │   │       └── [phone]/
│   │   │   │           └── page.tsx
│   │   │   ├── campaigns/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── loading.tsx
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx
│   │   │   └── settings/
│   │   │       └── page.tsx
│   │   │
│   │   └── middleware.ts                 # Auth guard: (app) → /login redirect
│   │
│   ├── components/
│   │   ├── ui/                           # Atomic (shadcn/ui + custom)
│   │   │   ├── badge.tsx
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── data-table.tsx
│   │   │   ├── input.tsx
│   │   │   ├── label.tsx
│   │   │   ├── select.tsx
│   │   │   ├── skeleton.tsx
│   │   │   ├── status-dot.tsx            # Ping-dot indicator (custom)
│   │   │   ├── table.tsx
│   │   │   └── tabs.tsx
│   │   │
│   │   ├── landing/                      # Landing page sections
│   │   │   ├── navbar.tsx                # Sticky nav + blur backdrop
│   │   │   ├── hero.tsx                  # Headline + CTA + animated mock
│   │   │   ├── features.tsx              # 4 feature cards
│   │   │   ├── how-it-works.tsx          # 3 steps
│   │   │   ├── pricing.tsx              # 3 tiers
│   │   │   ├── dashboard-preview.tsx     # Animated mock dashboard in hero
│   │   │   └── footer.tsx
│   │   │
│   │   ├── auth/                         # Auth components
│   │   │   └── login-form.tsx            # Email + password + submit
│   │   │
│   │   ├── layout/                       # App layout
│   │   │   ├── sidebar.tsx               # Collapsible nav
│   │   │   ├── nav-item.tsx
│   │   │   └── shell.tsx                 # Sidebar + content wrapper
│   │   │
│   │   ├── dashboard/                    # Dashboard feature
│   │   │   ├── kpi-card.tsx
│   │   │   ├── kpi-grid.tsx
│   │   │   ├── timeline-chart.tsx
│   │   │   ├── funnel-chart.tsx
│   │   │   └── campaigns-overview.tsx
│   │   │
│   │   ├── conversations/                # Chat feature
│   │   │   ├── conversation-list.tsx
│   │   │   ├── conversation-card.tsx
│   │   │   ├── chat-view.tsx
│   │   │   ├── message-bubble.tsx
│   │   │   └── chat-header.tsx
│   │   │
│   │   ├── campaigns/                    # Campaigns feature
│   │   │   ├── campaign-card.tsx
│   │   │   ├── campaign-stats.tsx
│   │   │   ├── recipients-table.tsx
│   │   │   └── status-funnel.tsx
│   │   │
│   │   └── shared/                       # Cross-feature
│   │       ├── empty-state.tsx
│   │       ├── page-header.tsx
│   │       ├── animated-number.tsx
│   │       └── page-transition.tsx
│   │
│   ├── hooks/
│   │   ├── use-api.ts                    # SWR fetcher + auth header
│   │   ├── use-auth.ts                   # Login, logout, token management
│   │   ├── use-websocket.ts
│   │   ├── use-dashboard.ts
│   │   ├── use-campaigns.ts
│   │   ├── use-conversations.ts
│   │   └── use-debounce.ts
│   │
│   ├── lib/
│   │   ├── api-client.ts                # fetch() + auth + base URL
│   │   ├── auth.ts                       # Token helpers (get/set/remove)
│   │   ├── utils.ts                      # cn() + helpers
│   │   ├── constants.ts                  # Status colors, routes, labels
│   │   └── formatters.ts                 # Number, date, phone formatting
│   │
│   ├── types/
│   │   ├── api.ts
│   │   ├── auth.ts                       # LoginRequest, AuthResponse
│   │   ├── campaign.ts
│   │   ├── conversation.ts
│   │   └── dashboard.ts
│   │
│   └── styles/
│       └── globals.css                   # Tailwind + CSS vars + dot grid
│
├── middleware.ts                          # Next.js middleware (auth check)
├── tailwind.config.ts
├── next.config.js
├── tsconfig.json
├── package.json
├── components.json                       # shadcn/ui config
└── .env.local                            # API_URL, NEXT_PUBLIC_API_URL
```

### Ключевые архитектурные решения

| Решение | Обоснование |
|---------|-------------|
| **Route groups** `(auth)` / `(app)` | Разные layouts: auth = centered card, app = sidebar shell. Landing = root |
| **middleware.ts** | Next.js middleware проверяет JWT cookie, redirect `/login` если нет токена |
| **SWR** вместо React Query | Проще API, встроенная ревалидация, меньше boilerplate |
| **WebSocket → SWR mutate** | WS-хук слушает события и вызывает `mutate()` для ключей |
| **Feature-based компоненты** | `components/landing/`, `components/dashboard/` — по фичам |
| **shadcn/ui + custom** | shadcn для примитивов, кастомные для domain-specific |
| **CSS variables для темы** | Один globals.css — вся палитра Signal Grid |

### Data Flow

```
                    ┌── Landing (/) ── публичная, без API
                    │
User ──→ Next.js ──┤── Login (/login) ──→ POST /api/auth/login ──→ JWT cookie
                    │
                    └── App (/dashboard, ...) ──→ middleware проверяет JWT
                         │
                         ├── SWR hooks ──→ API (fetch + Bearer token)
                         │                        ↑
                         └── WebSocket ──→ SWR mutate() ──→ rerender
```

---

## 8. Данные и масштаб

### Текущие объёмы (реальные данные)

| Метрика | Значение | Влияние на UI |
|---------|----------|---------------|
| Кампаний | 1 | Пагинация не нужна, но заложена |
| Recipients | 20 | Одна страница таблицы |
| С диалогами | 14 | Список помещается без скролла |
| Макс. сообщений | 8 | Нет проблем с рендером |
| Компаний в кеше | 783 (5 файлов) | Пагинация по 50 |

### Проектируемый масштаб

| Метрика | Ожидание | Подход |
|---------|----------|--------|
| Кампаний | до 50 | Пагинация по 12 карточек |
| Recipients | до 500 на кампанию | DataTable с пагинацией по 20 |
| Диалогов | до 200 | Виртуализация не нужна, простой список с пагинацией |
| Сообщений | до 30 на диалог | Нет проблем |

> **Виртуализация не нужна** при текущих и ожидаемых объёмах. Простая пагинация + SWR кеширование.

---

## 9. Порядок реализации

| Этап | Что делаем | Зависимости |
|------|-----------|-------------|
| 1 | Next.js init + Tailwind + shadcn/ui + Geist fonts + globals.css (тема) | — |
| 2 | **Landing page** — navbar, hero (с animated mock), features, pricing, footer | Этап 1 |
| 3 | **Auth** — backend JWT endpoint + frontend login page + middleware | Этап 1 |
| 4 | Layout Shell: sidebar + nav + shell + dot grid background | Этап 1, 3 |
| 5 | Hooks + API client + types (с auth header) | Этап 3 |
| 6 | Dashboard: KPI cards + timeline chart + funnel + campaign table | Этап 4, 5 |
| 7 | Campaigns: list cards + detail page + recipients table | Этап 4, 5 |
| 8 | Conversations: split panel + list + chat view + message bubbles | Этап 4, 5 |
| 9 | Settings: health status + accounts list | Этап 4, 5 |
| 10 | WebSocket integration + live updates + animations polish | Этапы 6-9 |

### Почему лендинг первым
- Мгновенный визуальный результат — можно показать инвесторам после этапа 2
- Не требует backend auth — работает standalone
- Определяет визуальный язык, который потом переиспользуется в app

### Переход на SaaS (будущее)
| Что добавить | Описание |
|-------------|----------|
| Регистрация | `/register` страница, email confirmation |
| Мультитенантность | `user_id` в данных, изоляция кампаний |
| Биллинг | Stripe/ЮKassa интеграция, планы подписки |
| PostgreSQL | Миграция с JSON на БД, user table |
| Лендинг CTA | "Начать бесплатно" → реальная регистрация |
| Admin panel | Управление пользователями, метрики платформы |
