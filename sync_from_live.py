import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

REMOTE_BASE = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/dev_whatsapp_chatbot_ent/models'
LOCAL_BASE  = r'C:\odoo19\addons\dev_whatsapp_chatbot_ent\models'

files = [
    'wa_chatbot_session.py',
    'chatbot_processor.py',
]

sftp = ssh.open_sftp()

for fname in files:
    remote_path = f'{REMOTE_BASE}/{fname}'
    local_path  = os.path.join(LOCAL_BASE, fname)

    # Read from server
    with sftp.open(remote_path, 'r') as rf:
        content = rf.read().decode('utf-8', errors='replace')

    # Write locally
    with open(local_path, 'w', encoding='utf-8', newline='\n') as lf:
        lf.write(content)

    local_size  = os.path.getsize(local_path)
    print(f'[OK] {fname}  ->  {local_path}  ({local_size:,} bytes)')

sftp.close()
ssh.close()
print('\nAll done. Local files are now in sync with the live server.')
