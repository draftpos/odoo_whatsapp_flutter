import paramiko
import json

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

cmd = "docker inspect psql_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
out = stdout.read().decode()
try:
    data = json.loads(out)
    for k, v in data[0]['NetworkSettings']['Networks'].items():
        print(f"Network: {k}, IP: {v['IPAddress']}")
except Exception as e:
    print(e)
    print(out)

client.close()
