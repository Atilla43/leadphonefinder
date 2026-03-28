# Архитектура бота

## Обзор

Бот состоит из двух слоёв:
1. **aiogram** (Bot API) — интерфейс пользователя: меню, кнопки, FSM, загрузка файлов
2. **telethon** (userbot) — рассылка сообщений от имени пользовательских аккаунтов + слушатель ответов

## Запуск

```bash
python -m bot.main
```

На сервере — systemd-сервис `leadbot`:
```
WorkingDirectory=/root/LeadPhoneFinder
ExecStart=/root/LeadPhoneFinder/venv/bin/python -m bot.main
```

### Процесс запуска (`bot/main.py`)

1. Создаётся aiogram `Bot` + `Dispatcher`
2. Регистрируются роутеры: `start`, `file_upload`, `callbacks`, `scrapper`, `outreach`
3. При startup:
   - Подключается пул Telethon-аккаунтов (`AccountPool.connect_all()`)
   - Загружаются активные кампании из `data/outreach/*.json`
   - Восстанавливаются счётчики `sent_today`
   - Для каждой кампании создаётся `OutreachService` + `AISalesEngine`
   - Запускаются listener'ы входящих сообщений
   - Запускаются ping-loop'ы
   - Если кампания была в `sending` — продолжает рассылку
4. Запускается long-polling

## Функциональные модули

### 1. Обогащение (Enrichment)

**Поток:** Пользователь загружает Excel/CSV с ИНН → бот ищет телефоны через Sherlock → возвращает обогащённый файл.

```
Excel/CSV → file_parser → Company[] → enrichment → Sherlock API/Telegram → результат Excel
```

- **Sherlock API** (приоритет): HTTP API на `api-dyxless.cfd`, 2₽/запрос, 100 запросов/15 мин
- **Sherlock Telegram** (fallback): Telethon-клиент отправляет ИНН боту `@sherlock_osint_bot`
- Результат: телефон, email, ФИО контактов, адреса, юр. данные

### 2. Скраппер (Scrapper)

**Поток:** Пользователь вводит запрос → Playwright парсит 2ГИС и Яндекс.Карты → дедупликация → поиск ИНН → Excel.

```
Запрос → QueryParser → [TwoGisScrapper, YandexMapsScrapper] → Deduplicator → InnFinder (DaData) → Excel
```

- Парсинг через headless Playwright (Chromium)
- Извлечение данных через JavaScript из DOM
- Кеш результатов в `data/cache/` (TTL 24 часа)

### 3. AI-рассылка (Outreach) — КЛЮЧЕВОЙ МОДУЛЬ

Самый сложный модуль. Три фазы работы:

#### Фаза 1: Рассылка первых сообщений

```
recipients[] → для каждого:
  1. normalize_phone(phone)
  2. ImportContactsRequest — resolve телефона в Telegram user
  3. Если не найден → status = "not_found"
  4. Отправка первого сообщения (render_first_message)
  5. status = "sent"
  6. Задержка (растянуто на рабочий день 10:00-17:00 МСК)
```

**Особенности:**
- Round-robin по аккаунтам (`AccountPool.get_next_available()`)
- Дневной лимит: `outreach_daily_limit` на аккаунт (по умолчанию 30)
- Автоматическая пауза на ночь (вне рабочих часов)
- Обработка FloodWait от Telegram
- Расчёт интервала: `remaining_seconds / sends_planned` (минимум 30 сек)

#### Фаза 2a: Слушатель ответов (Listener)

```
telethon event handler (incoming messages) →
  1. Поиск recipient по sender_id
  2. Извлечение текста (+ контакт-карточка, + транскрибация голосовых)
  3. Дебаунс 30 сек (ждём все сообщения от лида)
  4. AISalesEngine.generate_response() → JSON {reply, status}
  5. Отправка ответа с имитацией набора текста
  6. Обновление статуса: talking → warm → warm_confirmed / rejected
```

**Обработка статусов:**
- `talking` — продолжаем диалог
- `warm` — уведомление менеджеру, статус → `warm_confirmed`
- `rejected` — завершаем (3+ отказа или "бизнес закрыт")
- `referral` — LLM извлекает контакт, создаёт нового recipient, пишет ему

#### Фаза 2b: Автопинг (Ping Loop)

```
Каждые outreach_ping_interval_hours (4ч):
  Для каждого recipient со status="sent" и без ответа:
    1. Если ping_count >= max_pings (3) → status = "no_response"
    2. Иначе: AISalesEngine.generate_followup() → отправка
    3. ping_count += 1
```

### 4. AI Sales Engine

**LLM через OpenRouter** (OpenAI-совместимый API):
- Модель по умолчанию: `openai/gpt-4o-mini`
- temperature: 0.9
- response_format: JSON
- 4 промпта:
  - `SALES_SYSTEM_PROMPT` — основной диалог продаж
  - `FOLLOWUP_SYSTEM_PROMPT` — follow-up при игноре
  - `REFERRAL_FIRST_MSG_PROMPT` — первое сообщение для referral
  - `REFERRAL_EXTRACT_PROMPT` — извлечение контакта из сообщений

**Персонализация:**
- `company_context` — данные о компании (категория, рейтинг, сайт)
- `service_info` — информация об услугах и ценах
- `custom_system_prompt` — пользовательский промпт

### 5. Voice Transcription

Голосовые сообщения от лидов → Groq Whisper API → текст:
- Модель: `whisper-large-v3`
- Язык: `ru`
- Результат добавляется как `[голосовое] текст`

### 6. Account Pool

Мульти-аккаунтная рассылка:
- Round-robin распределение получателей
- Дневной лимит на каждый аккаунт
- Автоматическая миграция из `.env` при первом запуске
- Добавление/удаление аккаунтов через бота (FSM)
- Обработка бана аккаунтов

## Уведомления

Бот отправляет уведомления владельцу кампании и менеджерам при:
- `first_reply` — первый ответ лида
- `warm_lead` / `warm_lead_reply` — лид заинтересован
- `referral` — лид дал контакт другого человека
- `flood_wait` — rate limit от Telegram
- `daily_limit` — достигнут дневной лимит
- `sending_complete` — рассылка завершена

## Восстановление после рестарта

При запуске бот:
1. Загружает все кампании с `status in (sending, listening, paused)`
2. Восстанавливает `sent_today` счётчики
3. Resolve'ит `telegram_user_id` для recipients без него
4. Перезапускает listener'ы и ping-loop'ы
5. Для `sending` кампаний — продолжает рассылку (`resume=True`)
6. Отвечает на неотвеченные сообщения лидов (`retry_unanswered()`)
