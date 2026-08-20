import paramiko
import time

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

cmd1 = "docker restart odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
client.exec_command(cmd1, timeout=60)

time.sleep(10)

cmd2 = "docker logs --tail 50 odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
stdin, stdout, stderr = client.exec_command(cmd2, timeout=60)
out = stdout.read().decode()
err = stderr.read().decode()

print("STDOUT:")
print(out)
if err:
    print("STDERR:")
    print(err)

client.close()
