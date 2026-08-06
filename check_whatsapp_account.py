import os
import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

cmd = "docker exec odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke cat /mnt/extra-addons/whatsapp_web_chats/models/whatsapp_account.py"
stdin, stdout, stderr = ssh.exec_command(cmd)
with open('whatsapp_account_server.py', 'w', encoding='utf-8') as f:
    f.write(stdout.read().decode('utf-8'))

ssh.close()
