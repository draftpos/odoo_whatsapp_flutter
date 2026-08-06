import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

files_to_sync = [
    ('whatsapp_web_chats/models/mail_message.py', r'C:\odoo19\addons\whatsapp_web_chats\models\mail_message.py'),
]

REMOTE_BASE = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons'
sftp = ssh.open_sftp()

for remote_rel, local_path in files_to_sync:
    remote_path = f'{REMOTE_BASE}/{remote_rel}'
    try:
        with open(local_path, 'r', encoding='utf-8') as lf:
            content = lf.read()
        with sftp.open(remote_path, 'w') as rf:
            rf.write(content.encode('utf-8'))
        print(f'[OK] Uploaded {remote_rel}')
    except Exception as e:
        print(f'[ERROR] Failed to upload {remote_rel}: {e}')

sftp.close()

# Restart the Odoo Docker container
CONTAINER = 'odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke'
print("Restarting Odoo container...")
stdin, stdout, stderr = ssh.exec_command(f'docker restart {CONTAINER}')
print(stdout.read().decode('utf-8'))
print(stderr.read().decode('utf-8'))

ssh.close()
print('Done uploading modified files and restarting Odoo.')
