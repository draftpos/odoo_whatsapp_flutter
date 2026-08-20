import paramiko
import time

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=30)

# The real DB name is demo1_havano_pro_pknuzuhckrvwadhoboithcke
# The current upgrade running uses that - wait for it to finish, then check

cmd = r"""
CONTAINER="odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
DB_CONTAINER="psql_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
DB_NAME="demo1_havano_pro_pknuzuhckrvwadhoboithcke"

echo "=== Waiting for current upgrade to finish ==="
for i in $(seq 1 30); do
  PIDS=$(docker exec $CONTAINER pgrep -f "stop-after-init" 2>/dev/null)
  if [ -z "$PIDS" ]; then
    echo "Upgrade process done after $i checks"
    break
  fi
  echo "Still running... waiting (attempt $i)"
  sleep 5
done

echo ""
echo "=== Check ir_ui_view for our custom templates ==="
docker exec $DB_CONTAINER psql -U odoo -d demo1_havano_pro_pknuzuhckrvwadhoboithcke -c "SELECT name, key FROM ir_ui_view WHERE key LIKE '%custom_student%' OR key LIKE '%custom_fees%' OR key LIKE '%partner_ledger%';" 2>&1

echo ""
echo "=== Check report actions with correct DB name ==="
docker exec $DB_CONTAINER psql -U odoo -d demo1_havano_pro_pknuzuhckrvwadhoboithcke -c "SELECT name, report_name FROM ir_act_report_xml WHERE report_name LIKE '%partner_ledger%' OR report_name LIKE '%fees_structure%';" 2>&1

echo ""
echo "=== Restart container ==="
docker restart $CONTAINER
echo "Restarted!"
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
out = stdout.read().decode()
err = stderr.read().decode()
print("STDOUT:")
print(out if out else "(empty)")
if err:
    print("STDERR:", err[:3000])
client.close()
