#!/bin/bash
# Скрипт деплоя LeadPhoneFinder на Ubuntu 24.04
set -e

APP_DIR="/root/LeadPhoneFinder"
SERVICE_NAME="leadbot"

echo "=== 1. Установка системных пакетов ==="
apt update -y
apt install -y python3 python3-venv python3-pip git

echo "=== 2. Клонирование/обновление проекта ==="
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR"
    git pull origin main
else
    git clone https://github.com/Atilla43/leadphonefinder.git "$APP_DIR"
    cd "$APP_DIR"
fi

echo "=== 3. Виртуальное окружение ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== 4. Создание директорий ==="
mkdir -p data/outreach data/cache

echo "=== 5. Проверка .env ==="
if [ ! -f .env ]; then
    echo "ОШИБКА: .env не найден!"
    echo "Скопируйте .env на сервер: scp .env root@155.212.230.128:$APP_DIR/.env"
    exit 1
fi

echo "=== 6. Создание systemd сервиса ==="
cat > /etc/systemd/system/${SERVICE_NAME}.service << 'SERVICEEOF'
[Unit]
Description=LeadPhoneFinder Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/LeadPhoneFinder
ExecStart=/root/LeadPhoneFinder/venv/bin/python -m bot.main
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}

echo "=== 7. Запуск бота ==="
systemctl restart ${SERVICE_NAME}
sleep 2
systemctl status ${SERVICE_NAME} --no-pager

echo ""
echo "=== ГОТОВО ==="
echo "Бот запущен! Команды:"
echo "  Логи:      journalctl -u ${SERVICE_NAME} -f"
echo "  Статус:    systemctl status ${SERVICE_NAME}"
echo "  Рестарт:   systemctl restart ${SERVICE_NAME}"
echo "  Стоп:      systemctl stop ${SERVICE_NAME}"
