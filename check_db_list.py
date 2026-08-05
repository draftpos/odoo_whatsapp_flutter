import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***')

# Query to list databases
stdin, stdout, stderr = ssh.exec_command("docker exec -i odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke psql -U odoo -l")
print("DATABASES:\n", stdout.read().decode(errors="ignore"))
print("STDERR:\n", stderr.read().decode(errors="ignore"))
ssh.close()
