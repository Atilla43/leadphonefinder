"""Миграционный скрипт: восстановление кампании 13.03 из логов.

Запустить ПЕРЕД перезапуском бота:
    python scripts/migrate_campaign.py

Создаёт data/outreach/campaign_590317122.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.models.outreach import OutreachCampaign, OutreachRecipient

USER_ID = 590317122

OFFER = """Я занимаюсь геомаркетингом и продвижением на картах, позволяя получить больше клиентов, обойдя конкурентов в поисковой выдаче.

Обратил внимание, что у вашей карточки на яндексе имеется потенциал для роста и подумал, что возможно вам было бы это интересно.

Если вам будет интересно, то могу рассказать и показать примеры, где нам удалось вырасти и увеличить кол-во новых клиентов в вашей нише"""

# --- Данные из логов 13.03.2026 ---

SENT_RECIPIENTS = [
    ("+79180376606", "Амир кебаб", "2026-03-13T10:04:00+00:00"),
    ("+79678049705", "Академия", "2026-03-13T10:04:12+00:00"),
    ("+79384195488", "Pandora Sushi", "2026-03-13T10:04:21+00:00"),
    ("+79183068739", "Еда от души", "2026-03-13T10:04:36+00:00"),
    ("+79184037260", "Прожарка", "2026-03-13T10:04:50+00:00"),
    ("+79787751822", "Старик Хинкалыч", "2026-03-13T10:04:57+00:00"),
    ("+79186002880", "Моё", "2026-03-13T10:05:07+00:00"),
    ("+79826230406", "Папина радость", "2026-03-13T10:05:15+00:00"),
    ("+79384599975", "Ламаджо", "2026-03-13T10:05:25+00:00"),
    ("+79883554448", "Море ролл", "2026-03-13T10:05:33+00:00"),
    ("+79654689897", "Шаурмянка", "2026-03-13T10:05:46+00:00"),
    ("+79384026165", "Колибри", "2026-03-13T10:05:55+00:00"),
    ("+79227968204", "Этолето", "2026-03-13T10:06:08+00:00"),
    ("+79672271313", "Frutinie", "2026-03-13T10:06:23+00:00"),
]

NOT_FOUND_PHONES = [
    "+79186112414",
    "+79996524697",
    "+79183031881",
    "+79884140767",
    "+79628898438",
    "+79181047009",
]


def build_first_message(company_name: str) -> str:
    """Воссоздаёт первое сообщение по шаблону."""
    return f"Здравствуйте, хочу коротко обсудить сотрудничество с «{company_name}».\n\n{OFFER}"


def main():
    recipients = []

    # Отправленные
    for phone, company, ts in SENT_RECIPIENTS:
        first_msg = build_first_message(company)
        r = OutreachRecipient(
            phone=phone,
            company_name=company,
            status="sent",
            last_message_at=datetime.fromisoformat(ts),
            conversation_history=[
                {"role": "assistant", "content": first_msg},
            ],
        )

        # Warm lead: Моё (telegram_user_id=307743867)
        if company == "Моё":
            r.telegram_user_id = 307743867
            r.status = "warm"
            r.conversation_history = [
                {"role": "assistant", "content": first_msg},
                {"role": "user", "content": "Здравствуйте, в принципе  интересно"},
                {"role": "assistant", "content": "Отлично! Как насчет короткого звонка на 15 минут? Завтра в 11 или 14 удобно?"},
            ]
            r.last_message_at = datetime.fromisoformat("2026-03-13T19:20:16+00:00")

        recipients.append(r)

    # Не в Telegram
    for phone in NOT_FOUND_PHONES:
        r = OutreachRecipient(
            phone=phone,
            company_name="",
            status="not_found",
        )
        recipients.append(r)

    campaign = OutreachCampaign(
        user_id=USER_ID,
        offer=OFFER,
        recipients=recipients,
        status="listening",
        sent_count=14,
        warm_count=1,
        rejected_count=0,
        not_found_count=6,
        manager_ids=[],
        system_prompt="",
    )

    # Сохраняем
    output_dir = Path("data/outreach")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"campaign_{USER_ID}.json"

    data = campaign.to_dict()
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Campaign saved to {output_path}")
    print(f"  Recipients: {len(recipients)} ({len(SENT_RECIPIENTS)} sent, {len(NOT_FOUND_PHONES)} not found)")
    print(f"  Warm leads: {campaign.warm_count}")
    print(f"  Status: {campaign.status}")
    print()
    print("Now restart the bot — it will restore this campaign automatically.")


if __name__ == "__main__":
    main()
