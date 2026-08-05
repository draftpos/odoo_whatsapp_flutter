import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

files_to_sync = [
    ('whatsapp_web_chats/static/src/xml/chats_template.xml', r'C:\odoo19\addons\whatsapp_web_chats\static\src\xml\chats_template.xml'),
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
ssh.close()
print('Done uploading chats_template.xml')
