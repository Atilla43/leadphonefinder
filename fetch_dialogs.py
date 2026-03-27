"""Скрипт для выгрузки всех диалогов с сервера для анализа."""
import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('155.212.230.128', username='root', password='QL1BIjx272*%', timeout=30)

script = """
import json, glob, os

results = {"campaigns": [], "stats": {}}
status_counts = {}
dialogs = []

for f in sorted(glob.glob('data/outreach/campaign_*.json')):
    data = json.load(open(f))
    camp_info = {
        "file": os.path.basename(f),
        "user_id": data.get("user_id"),
        "status": data.get("status"),
        "offer": data.get("offer", "")[:200],
        "sent_count": data.get("sent_count", 0),
        "warm_count": data.get("warm_count", 0),
        "rejected_count": data.get("rejected_count", 0),
        "not_found_count": data.get("not_found_count", 0),
        "total_recipients": len(data.get("recipients", [])),
    }
    results["campaigns"].append(camp_info)

    for r in data.get("recipients", []):
        st = r.get("status", "unknown")
        status_counts[st] = status_counts.get(st, 0) + 1

        history = r.get("conversation_history", [])
        user_msgs = [m for m in history if m.get("role") == "user"]

        if len(history) >= 2:
            dialogs.append({
                "company": r.get("company_name"),
                "contact": r.get("contact_name"),
                "status": st,
                "phone": r.get("phone"),
                "ping_count": r.get("ping_count", 0),
                "msg_count": len(history),
                "user_msg_count": len(user_msgs),
                "referral_context": r.get("referral_context"),
                "history": history,
            })

results["stats"] = status_counts
results["dialogs"] = sorted(dialogs, key=lambda x: x["msg_count"], reverse=True)
print(json.dumps(results, ensure_ascii=False, indent=2))
"""

sftp = ssh.open_sftp()
with sftp.file('/root/LeadPhoneFinder/fetch_tmp.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /root/LeadPhoneFinder && python3 fetch_tmp.py')
out = stdout.read().decode('utf-8')
err = stderr.read().decode('utf-8')
if err:
    print("STDERR:", err)

ssh.close()

# Save to local file
with open('dialogs_dump.json', 'w', encoding='utf-8') as f:
    f.write(out)

data = json.loads(out)
print(f"\n=== STATS ===")
for k, v in data["stats"].items():
    print(f"  {k}: {v}")
print(f"\n=== CAMPAIGNS: {len(data['campaigns'])} ===")
for c in data["campaigns"]:
    print(f"  {c['file']}: status={c['status']}, sent={c['sent_count']}, warm={c['warm_count']}, total={c['total_recipients']}")
print(f"\n=== DIALOGS WITH RESPONSES: {len(data['dialogs'])} ===")
for d in data["dialogs"]:
    print(f"  {d['company']} ({d['contact'] or '?'}): status={d['status']}, msgs={d['msg_count']}, user_msgs={d['user_msg_count']}")
