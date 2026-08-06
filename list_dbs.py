import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password=os.environ.get('SERVER_PASSWORD'))

cmd = "docker exec -i -e PGPASSWORD=odoo odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke psql -h db -U odoo -l"
print(f"Running: {cmd}")
stdin, stdout, stderr = ssh.exec_command(cmd)

print("STDOUT:")
for line in stdout:
    print(line, end="")

print("STDERR:")
for line in stderr:
    print(line, end="")

ssh.close()
