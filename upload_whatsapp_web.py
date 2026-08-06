import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

# We only need to upload the files we actually changed
files_to_sync = [
    'whatsapp_web_chats/static/src/js/chats.js',
    'whatsapp_web_chats/static/src/xml/chats_template.xml',
    'whatsapp_web_chats/static/src/css/chats.css',
    'whatsapp_web_chats/models/whatsapp_account.py',
    'whatsapp_web_chats/models/__init__.py',
    'whatsapp_web_chats/models/mail_message.py',
    'whatsapp_web_chats/models/whatsapp_message.py',
]

REMOTE_BASE = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons'
LOCAL_BASE = r'C:\odoo19\addons'

sftp = ssh.open_sftp()

for f in files_to_sync:
    remote_path = f'{REMOTE_BASE}/{f}'
    local_path = os.path.join(LOCAL_BASE, f.replace('/', '\\'))
    
    try:
        # Read the updated local file
        with open(local_path, 'r', encoding='utf-8') as lf:
            content = lf.read()
            
        # Write to the remote server
        with sftp.open(remote_path, 'w') as rf:
            rf.write(content.encode('utf-8'))
            
        print(f'[OK] Uploaded {f} to remote server.')
    except Exception as e:
        print(f'[ERROR] Failed to upload {f}: {e}')

sftp.close()
ssh.close()
print('Done uploading modified files.')
