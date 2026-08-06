import os
import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

# Read the current wa_chatbot_session.py
fpath = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/dev_whatsapp_chatbot_ent/models/wa_chatbot_session.py'
stdin, stdout, stderr = ssh.exec_command(f'cat {fpath}')
content = stdout.read().decode('utf-8', errors='replace')

# Show the cron section we need to fix
lines = content.split('\n')
for i, line in enumerate(lines):
    if '_cron_expire_sessions' in line or "state', '=', 'active'" in line:
        print(f"Line {i+1}: {line}")

ssh.close()
