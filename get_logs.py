import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

stdin, stdout, stderr = ssh.exec_command('docker logs --tail 200 odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke')
print(stdout.read().decode('utf-8'))
print(stderr.read().decode('utf-8'))
ssh.close()
