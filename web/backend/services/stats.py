"""Агрегация статистики из данных кампаний."""

from collections import defaultdict
from datetime import datetime, timedelta

from services.data_reader import DataReader

REPLIED_STATUSES = {"talking", "warm", "warm_confirmed", "referral"}
WARM_STATUSES = {"warm", "warm_confirmed"}
ACTIVE_CAMPAIGN_STATUSES = {"sending", "listening", "paused"}

ALL_RECIPIENT_STATUSES = [
    "pending", "sent", "talking", "warm", "warm_confirmed",
    "referral", "rejected", "no_response", "not_found", "error",
]


def compute_dashboard_stats(reader: DataReader) -> dict:
    """Вычисляет общую статистику дашборда."""
    campaigns = reader.get_all_campaigns()

    total_recipients = 0
    total_sent = 0
    total_replied = 0
    total_warm = 0
    total_rejected = 0
    total_no_response = 0
    total_not_found = 0
    active = 0

    for c in campaigns:
        if c.get("status") in ACTIVE_CAMPAIGN_STATUSES:
            active += 1
        for r in c.get("recipients", []):
            total_recipients += 1
            status = r.get("status", "pending")
            if status not in ("pending", "not_found", "error"):
                total_sent += 1
            if status in REPLIED_STATUSES:
                total_replied += 1
            if status in WARM_STATUSES:
                total_warm += 1
            if status == "rejected":
                total_rejected += 1
            if status == "no_response":
                total_no_response += 1
            if status == "not_found":
                total_not_found += 1

    response_rate = (total_replied / total_sent * 100) if total_sent else 0.0
    conversion_rate = (total_warm / total_sent * 100) if total_sent else 0.0

    return {
        "total_campaigns": len(campaigns),
        "active_campaigns": active,
        "total_recipients": total_recipients,
        "total_sent": total_sent,
        "total_replied": total_replied,
        "total_warm": total_warm,
        "total_rejected": total_rejected,
        "total_no_response": total_no_response,
        "total_not_found": total_not_found,
        "response_rate": round(response_rate, 2),
        "conversion_rate": round(conversion_rate, 2),
    }


def compute_funnel(reader: DataReader) -> list[dict]:
    """Вычисляет воронку по статусам."""
    counts: dict[str, int] = defaultdict(int)
    total = 0

    for c in reader.get_all_campaigns():
        for r in c.get("recipients", []):
            total += 1
            counts[r.get("status", "pending")] += 1

    # replied = сумма всех кто ответил
    replied = sum(counts.get(s, 0) for s in REPLIED_STATUSES)
    sent = total - counts.get("pending", 0) - counts.get("not_found", 0) - counts.get("error", 0)

    labels = {
        "total": "Всего получателей",
        "sent": "Отправлено",
        "replied": "Ответили",
        "talking": "В диалоге",
        "warm": "Заинтересованы",
        "warm_confirmed": "Подтверждены",
        "referral": "Referral",
        "rejected": "Отказ",
        "no_response": "Без ответа",
        "not_found": "Не в Telegram",
    }

    stages = [
        {"stage": "total", "count": total, "label": labels["total"]},
        {"stage": "sent", "count": sent, "label": labels["sent"]},
        {"stage": "replied", "count": replied, "label": labels["replied"]},
    ]
    for status in ["talking", "warm", "warm_confirmed", "referral", "rejected", "no_response", "not_found"]:
        stages.append({
            "stage": status,
            "count": counts.get(status, 0),
            "label": labels.get(status, status),
        })

    return stages


def compute_timeline(
    reader: DataReader, days: int = 30, campaign_id: str | None = None,
) -> list[dict]:
    """Вычисляет динамику по дням из last_message_at."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    daily: dict[str, dict[str, int]] = defaultdict(lambda: {
        "sent": 0, "replied": 0, "warm": 0, "rejected": 0,
    })

    campaigns = reader.get_all_campaigns()
    for c in campaigns:
        cid = c.get("campaign_id") or str(c.get("user_id", ""))
        if campaign_id and cid != campaign_id:
            continue
        for r in c.get("recipients", []):
            lma = r.get("last_message_at")
            if not lma:
                continue
            try:
                dt = datetime.fromisoformat(lma.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue
            if dt.replace(tzinfo=None) < cutoff:
                continue
            date_str = dt.strftime("%Y-%m-%d")
            status = r.get("status", "pending")
            if status not in ("pending", "not_found", "error"):
                daily[date_str]["sent"] += 1
            if status in REPLIED_STATUSES:
                daily[date_str]["replied"] += 1
            if status in WARM_STATUSES:
                daily[date_str]["warm"] += 1
            if status == "rejected":
                daily[date_str]["rejected"] += 1

    # Заполняем пропущенные даты
    result: list[dict] = []
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        entry = daily.get(d, {"sent": 0, "replied": 0, "warm": 0, "rejected": 0})
        result.append({"date": d, **entry})

    return result
