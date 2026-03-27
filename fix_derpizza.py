"""Fix Derpizza: add missed messages to history and set status to talking."""
import json
import glob
from datetime import datetime, timezone

camp_file = glob.glob("data/outreach/campaign_*.json")[0]
camp = json.load(open(camp_file, encoding="utf-8"))

for r in camp["recipients"]:
    if "erpizza" in r.get("company_name", "").lower():
        combined = (
            "Добрый вечер Александр\n"
            "Derpizza у нас только в Яндекс еде есть\n"
            "И практический не работает"
        )
        r["conversation_history"].append({"role": "user", "content": combined})
        r["status"] = "talking"
        r["ping_count"] = 0
        r["last_message_at"] = datetime.now(timezone.utc).isoformat()
        print(f"Updated: status=talking, history={len(r['conversation_history'])} msgs")
        break

with open(camp_file, "w", encoding="utf-8") as f:
    json.dump(camp, f, ensure_ascii=False, indent=2)
print("Saved")
