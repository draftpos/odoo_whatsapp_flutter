import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

files_to_sync = [
    'whatsapp_web_chats/__manifest__.py',
    'whatsapp_web_chats/static/src/css/chats.css',
    'whatsapp_web_chats/static/src/js/chats.js',
    'whatsapp_web_chats/static/src/xml/chats_template.xml',
    'whatsapp_web_chats/models/product_template.py',
    'whatsapp_web_chats/models/__init__.py',
    'whatsapp_web_chats/models/whatsapp_account.py',
    'whatsapp_web_chats/__init__.py',
    'whatsapp_web_chats/views/chats_action.xml',
    'whatsapp_web_chats/views/whatsapp_account_views.xml',
    'whatsapp_web_chats/views/product_template_views.xml'
]

REMOTE_BASE = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons'
LOCAL_BASE = r'C:\odoo19\addons'

sftp = ssh.open_sftp()

for f in files_to_sync:
    remote_path = f'{REMOTE_BASE}/{f}'
    local_path = os.path.join(LOCAL_BASE, f.replace('/', '\\'))
    
    # Ensure local directory exists
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    try:
        # Read from remote
        with sftp.open(remote_path, 'r') as rf:
            content = rf.read().decode('utf-8', errors='replace')
            
        # Write local
        with open(local_path, 'w', encoding='utf-8', newline='\n') as lf:
            lf.write(content)
        print(f'[OK] Synced {f}')
    except Exception as e:
        print(f'[ERROR] Failed to sync {f}: {e}')

sftp.close()
ssh.close()
print('Done syncing whatsapp_web_chats files.')
