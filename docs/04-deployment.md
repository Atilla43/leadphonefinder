# Развёртывание

## Требования

### Минимальные
- Python 3.11+
- 2 GB RAM
- 10 GB диск
- Ubuntu 22.04 / Windows 10+

### Рекомендуемые для production
- VPS с 4 GB RAM
- SSD диск
- Выделенный IP
- Telegram Premium (для userbot)

---

## Установка

### 1. Клонирование

```bash
git clone <repository-url>
cd LeadPhoneFinder
```

### 2. Виртуальное окружение

```bash
python -m venv venv

# Linux/MacOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Зависимости

```bash
pip install -r requirements.txt

# Установка браузера для Playwright
playwright install chromium
```

### 4. Конфигурация

```bash
cp .env.example .env
```

Заполните `.env`:

```env
# === ОБЯЗАТЕЛЬНО ===

# Telegram Bot (получить у @BotFather)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Telethon (получить на https://my.telegram.org)
TELETHON_API_ID=12345678
TELETHON_API_HASH=abcdef1234567890abcdef1234567890
TELETHON_PHONE=+79001234567
TELETHON_SESSION_NAME=userbot_session

# Sherlock бот
SHERLOCK_BOT_USERNAME=sherlock_search_bot

# === ОПЦИОНАЛЬНО ===

# DaData (ускоряет поиск ИНН)
# Получить: https://dadata.ru/api/suggest/party/
DADATA_TOKEN=

# Whitelist пользователей (через запятую)
ALLOWED_USER_IDS=123456789,987654321

# Лимиты
MAX_ROWS=100
SCRAPPER_MAX_RESULTS=100
```

### 5. Первый запуск

При первом запуске Telethon запросит код подтверждения:

```bash
python -m bot.main

# Введите код из Telegram
# Сессия сохранится в файл userbot_session.session
```

---

## Запуск

### Разработка

```bash
python -m bot.main
```

### Production (systemd)

Создайте файл `/etc/systemd/system/leadphonefinder.service`:

```ini
[Unit]
Description=LeadPhoneFinder Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/LeadPhoneFinder
Environment=PATH=/home/ubuntu/LeadPhoneFinder/venv/bin
ExecStart=/home/ubuntu/LeadPhoneFinder/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Управление:

```bash
sudo systemctl daemon-reload
sudo systemctl enable leadphonefinder
sudo systemctl start leadphonefinder
sudo systemctl status leadphonefinder

# Логи
sudo journalctl -u leadphonefinder -f
```

### Production (Docker)

`Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей Playwright
RUN apt-get update && apt-get install -y \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgbm1 libasound2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

CMD ["python", "-m", "bot.main"]
```

`docker-compose.yml`:

```yaml
version: '3.8'

services:
  bot:
    build: .
    restart: always
    env_file:
      - .env
    volumes:
      - ./userbot_session.session:/app/userbot_session.session
```

Запуск:

```bash
docker-compose up -d
docker-compose logs -f
```

---

## Мониторинг

### Логи

```bash
# Systemd
sudo journalctl -u leadphonefinder -f --since "1 hour ago"

# Docker
docker-compose logs -f --tail 100
```

### Метрики для отслеживания

| Метрика | Нормальное значение |
|---------|---------------------|
| Время парсинга 100 компаний | < 5 минут |
| Процент найденных телефонов | 40-60% |
| Ошибки Sherlock | < 5% |
| Память бота | < 500 MB |

### Алерты (опционально)

Добавьте в код:

```python
import logging

# Отправка алертов в Telegram
async def send_alert(message: str):
    await bot.send_message(ADMIN_CHAT_ID, f"⚠️ Alert: {message}")
```

---

## Бэкапы

### Что бэкапить

| Файл | Важность | Описание |
|------|----------|----------|
| `.env` | Критично | Токены и ключи |
| `userbot_session.session` | Критично | Сессия Telethon |
| `logs/` | Опционально | Логи |

### Скрипт бэкапа

```bash
#!/bin/bash
BACKUP_DIR=/home/ubuntu/backups
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/leadphonefinder_$DATE.tar.gz \
    /home/ubuntu/LeadPhoneFinder/.env \
    /home/ubuntu/LeadPhoneFinder/*.session

# Удаление старых бэкапов (старше 7 дней)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

Добавьте в cron:

```bash
crontab -e
# Каждый день в 3:00
0 3 * * * /home/ubuntu/backup.sh
```

---

## Обновление

### Ручное

```bash
cd /home/ubuntu/LeadPhoneFinder
git pull origin main
pip install -r requirements.txt
sudo systemctl restart leadphonefinder
```

### Автоматическое (CI/CD)

GitHub Actions `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /home/ubuntu/LeadPhoneFinder
            git pull origin main
            pip install -r requirements.txt
            sudo systemctl restart leadphonefinder
```

---

## Troubleshooting

### Бот не отвечает

1. Проверьте токен: `echo $BOT_TOKEN`
2. Проверьте логи: `journalctl -u leadphonefinder -f`
3. Перезапустите: `systemctl restart leadphonefinder`

### Sherlock не возвращает телефоны

1. Проверьте сессию Telethon
2. Возможно, бот @sherlock_search_bot изменился
3. Проверьте задержки (увеличьте `REQUEST_DELAY_SECONDS`)

### Playwright падает

1. Установите зависимости: `playwright install-deps chromium`
2. Увеличьте RAM сервера
3. Проверьте headless режим

### DaData не работает

1. Проверьте токен
2. Проверьте лимиты (10k/день)
3. Используется ЕГРЮЛ fallback

---

## Безопасность

### Рекомендации

1. **Не коммитьте `.env`** — добавьте в `.gitignore`
2. **Ограничьте доступ** — используйте `ALLOWED_USER_IDS`
3. **Защитите сервер** — firewall, SSH ключи
4. **Обновляйте зависимости** — `pip install --upgrade`

### Firewall (ufw)

```bash
sudo ufw allow 22    # SSH
sudo ufw enable
```

Telegram работает через HTTPS, дополнительные порты не нужны.
