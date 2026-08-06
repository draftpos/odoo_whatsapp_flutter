import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password=os.environ.get('SERVER_PASSWORD'))

stdin, stdout, stderr = ssh.exec_command("docker exec odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke grep -rn 'def ' /usr/lib/python3/dist-packages/odoo/addons/whatsapp/models/")
print("STDOUT:", stdout.read().decode(errors="ignore"))
ssh.close()
