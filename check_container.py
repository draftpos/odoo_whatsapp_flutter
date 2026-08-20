import paramiko

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

# Check what the actual running command/process is inside the container
# and try different upgrade approaches
cmd = r"""
CONTAINER="odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
DB_NAME="demo1_havano_pro"

echo "=== Container status ==="
docker inspect $CONTAINER --format '{{.State.Status}}'

echo ""
echo "=== Running processes in container ==="
docker exec $CONTAINER ps aux 2>&1 | head -20

echo ""
echo "=== Odoo conf location ==="
docker exec $CONTAINER find / -name "odoo.conf" 2>/dev/null | head -5

echo ""
echo "=== Try upgrade with explicit log level ==="
docker exec -u odoo $CONTAINER odoo --version 2>&1

echo ""
echo "=== Check addons path ==="
docker exec $CONTAINER cat /etc/odoo/odoo.conf 2>/dev/null || docker exec $CONTAINER find / -name "odoo.conf" -exec cat {} \; 2>/dev/null | head -30
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
out = stdout.read().decode()
err = stderr.read().decode()
print("STDOUT:")
print(out if out else "(empty)")
if err:
    print("STDERR:", err[:2000])
client.close()
