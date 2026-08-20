import paramiko

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

cmd = "docker inspect odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke | grep -i env -A 20"
stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
out = stdout.read().decode()
err = stderr.read().decode()

print("STDOUT:")
print(out)
if err:
    print("STDERR:")
    print(err)

client.close()
