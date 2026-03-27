"""Деплой бота на удалённый сервер через SSH."""
import os
import sys
import paramiko
import stat

HOST = "155.212.230.128"
USER = "root"
PASS = "QL1BIjx272*%"
APP_DIR = "/root/LeadPhoneFinder"

# Файлы для копирования (локальный путь → удалённый путь)
FILES_TO_COPY = {
    ".env": f"{APP_DIR}/.env",
    "userbot_session.session": f"{APP_DIR}/userbot_session.session",
}


def safe_print(text):
    """Print with fallback for encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode('ascii'))


def run(ssh, cmd, check=True):
    """Execute command and print output."""
    safe_print(f">>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    if out.strip():
        safe_print(out.strip())
    if err.strip():
        safe_print(err.strip())
    if check and code != 0:
        safe_print(f"!!! Exit code: {code}")
    return out, err, code


def upload_file(sftp, local_path, remote_path):
    """Загружает файл на сервер."""
    if not os.path.exists(local_path):
        print(f"SKIP: {local_path} not found")
        return False
    # Создаём директории
    remote_dir = os.path.dirname(remote_path)
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        # Создаём рекурсивно
        parts = remote_dir.split("/")
        current = ""
        for part in parts:
            if not part:
                current = "/"
                continue
            current = current + part + "/"
            try:
                sftp.stat(current)
            except FileNotFoundError:
                sftp.mkdir(current)

    print(f"UPLOAD: {local_path} -> {remote_path}")
    sftp.put(local_path, remote_path)
    return True


def main():
    print(f"=== Connecting to {HOST} ===")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    print("Connected!\n")

    # 1. Установка пакетов
    print("=== 1. System packages ===")
    run(ssh, "apt update -y -qq", check=False)
    run(ssh, "apt install -y -qq python3 python3-venv python3-pip git")

    # 2. Клонирование/обновление
    print("\n=== 2. Project code ===")
    _, _, code = run(ssh, f"test -d {APP_DIR} && echo EXISTS", check=False)
    out, _, _ = run(ssh, f"test -d {APP_DIR} && echo EXISTS || echo NO", check=False)
    if "EXISTS" in out:
        run(ssh, f"cd {APP_DIR} && git pull origin main")
    else:
        run(ssh, f"git clone https://github.com/Atilla43/leadphonefinder.git {APP_DIR}")

    # 3. Виртуальное окружение
    print("\n=== 3. Python venv ===")
    run(ssh, f"cd {APP_DIR} && python3 -m venv venv")
    run(ssh, f"cd {APP_DIR} && venv/bin/pip install --upgrade pip -q")
    run(ssh, f"cd {APP_DIR} && venv/bin/pip install -r requirements.txt -q")

    # 4. Создание директорий
    print("\n=== 4. Directories ===")
    run(ssh, f"mkdir -p {APP_DIR}/data/outreach {APP_DIR}/data/cache")

    # 5. Копирование файлов
    print("\n=== 5. Uploading data ===")
    sftp = ssh.open_sftp()
    for local, remote in FILES_TO_COPY.items():
        upload_file(sftp, local, remote)
    sftp.close()

    # 6. Systemd сервис
    print("\n=== 6. Systemd сервис ===")
    service_content = """[Unit]
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
"""
    run(ssh, f"cat > /etc/systemd/system/leadbot.service << 'SERVICEEOF'\n{service_content}SERVICEEOF")
    run(ssh, "systemctl daemon-reload")
    run(ssh, "systemctl enable leadbot")

    # 7. Запуск
    print("\n=== 7. Запуск бота ===")
    run(ssh, "systemctl restart leadbot")

    import time
    time.sleep(3)
    run(ssh, "systemctl status leadbot --no-pager", check=False)

    print("\n=== 8. Recent logs ===")
    run(ssh, "journalctl -u leadbot -n 20 --no-pager", check=False)

    ssh.close()
    print("\n=== DONE! Bot is running on the server ===")


if __name__ == "__main__":
    main()
