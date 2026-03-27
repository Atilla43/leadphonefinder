"""Скрипт для поиска данных лида на сервере."""
import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('155.212.230.128', username='root', password='QL1BIjx272*%', timeout=30)

script = r"""
import json, glob
for f in glob.glob('data/outreach/campaign_*.json'):
    data = json.load(open(f))
    for r in data.get('recipients', []):
        if '9603475557' in r.get('phone', ''):
            print(json.dumps(r, ensure_ascii=False, indent=2))
"""

sftp = ssh.open_sftp()
with sftp.file('/root/LeadPhoneFinder/find_lead_tmp.py', 'w') as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('cd /root/LeadPhoneFinder && python3 find_lead_tmp.py')
out = stdout.read()
print(out.decode('utf-8'))
ssh.close()
