# Два исправления: текст первого сообщения + next_send_at при восстановлении

## 1. Изменение текста первого сообщения

### Файл: `bot/services/outreach.py` — функция `render_first_message` (строка 82)

**Было:**
```
{greeting}, хочу коротко обсудить сотрудничество с «{company}».
```

**Стало:**
```
{greeting}, коротко по «{company}».
```

## 2. `next_send_at` не показывается — рассылка не возобновляется после перезапуска

### Проблема

При восстановлении кампании со статусом `sending` в `bot/main.py` (`on_startup`) вызываются только `start_listener()` и `_ping_loop()`. Сам цикл рассылки (`start_campaign`) **не перезапускается**, поэтому:
- Оставшиеся `pending` получатели не получат сообщения
- `next_send_at` остаётся `None`

### Решение

В `bot/main.py`, в `on_startup`, если `campaign.status == "sending"` — запустить `start_campaign` в фоне (через `asyncio.create_task`).

Но `start_campaign` принимает `campaign` и вызывает `start_listener`/`_ping_loop` внутри себя. Нужно добавить метод `resume_sending()` в `OutreachService`, который:
- Устанавливает `self._campaign` (уже установлен)
- НЕ вызывает `start_listener` повторно (уже запущен)
- Продолжает цикл отправки `pending` получателей

Проще: добавить флаг `resume=True` в `start_campaign` чтобы пропустить инициализацию listener/ping.

### Файл: `bot/services/outreach.py` — `start_campaign`

Добавить параметр `resume: bool = False`:
```python
async def start_campaign(self, campaign, progress_callback=None, resume=False):
    ...
    if not resume:
        # Распределяем получателей (при resume уже распределены)
        pool.assign_recipients(campaign.recipients, settings.outreach_daily_limit)
        self._save()
        await self.start_listener()
        self._ping_task = asyncio.create_task(self._ping_loop())
```

### Файл: `bot/main.py` — `on_startup`

После восстановления listener/ping, если `campaign.status == "sending"`:
```python
if campaign.status == "sending":
    asyncio.create_task(service.start_campaign(campaign, resume=True))
```

## Файлы для изменения

1. `bot/services/outreach.py` — `render_first_message` (текст) + `start_campaign` (параметр `resume`)
2. `bot/main.py` — `on_startup` (перезапуск рассылки)

## Проверка

- Перезапустить бота → рассылка должна продолжиться
- Нажать Статус → должен показать прогресс-бар и время следующей отправки
