import paramiko
import sys

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

cmd = "docker exec odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke odoo -u havano_schools_odoo -d demo1_havano_pro_pknuzuhckrvwadhoboithcke --stop-after-init"
print("Running:", cmd)
stdin, stdout, stderr = client.exec_command(cmd, get_pty=True, timeout=120)

for line in iter(stdout.readline, ""):
    print(line, end="")

client.close()
