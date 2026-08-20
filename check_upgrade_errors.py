import paramiko

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

# Step 1: Run upgrade and capture BOTH stdout and stderr fully
cmd = r"""
CONTAINER="odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
DB_NAME="demo1_havano_pro"

echo "=== Running module upgrade - capturing all output ==="
docker exec -u odoo $CONTAINER odoo \
  -u havano_schools_odoo \
  -d $DB_NAME \
  -c /etc/odoo/odoo.conf \
  --db_host=db --db_user=odoo --db_password=odoo \
  --stop-after-init --http-port=8070 2>&1 | grep -E "(ERROR|WARNING|Traceback|File|havano|custom_student|custom_fees|partner_ledger)" | tail -60
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=180)
out = stdout.read().decode()
err = stderr.read().decode()
print("STDOUT:")
print(out if out else "(empty)")
print("STDERR:")
print(err[:3000] if err else "(empty)")
client.close()
