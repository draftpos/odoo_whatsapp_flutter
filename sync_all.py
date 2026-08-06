import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

# Tar the modules on the remote server
cmds = [
    'cd /home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons && tar -czf whatsapp_mods.tar.gz whatsapp whatsapp_web_chats dev_whatsapp_chatbot_ent'
]
for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.read()
    stderr.read()

sftp = ssh.open_sftp()
remote_tar = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/whatsapp_mods.tar.gz'
local_tar = r'C:\odoo19\addons\whatsapp_mods.tar.gz'
print('Downloading tar file...')
sftp.get(remote_tar, local_tar)
sftp.close()

# Cleanup remote tar
ssh.exec_command(f'rm {remote_tar}')
ssh.close()
print('Download complete.')
