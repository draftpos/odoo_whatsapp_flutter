import os
import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password=os.environ.get('SERVER_PASSWORD'))

# Connect to odoo database and check ir_module_module
stdin, stdout, stderr = ssh.exec_command("docker exec -i odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke psql -U odoo -d demo1_havano_pro -c \"SELECT name, state FROM ir_module_module WHERE state = 'installed' AND name LIKE '%whatsapp%';\"")
print(stdout.read().decode(errors="ignore"))
ssh.close()
