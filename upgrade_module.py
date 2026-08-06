import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password=os.environ.get('SERVER_PASSWORD'))

print("Executing upgrade command...")
stdin, stdout, stderr = ssh.exec_command('docker exec -u odoo odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke odoo -c /etc/odoo/odoo.conf -d demo1 -u whatsapp_web_chats --stop-after-init')
print("STDOUT:", stdout.read().decode(errors='ignore'))
print("STDERR:", stderr.read().decode(errors='ignore'))
ssh.close()
