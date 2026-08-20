import paramiko

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

# Step 1: Wait for DB to be ready, then force upgrade
cmd = """
CONTAINER="odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
DB_CONTAINER="psql_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
DB_NAME="demo1_havano_pro"

echo "=== Waiting for DB to be fully ready ==="
sleep 5

# Check DB is up
for i in 1 2 3 4 5; do
  STATUS=$(docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT 1;" 2>&1)
  echo "DB check attempt $i: $STATUS"
  if echo "$STATUS" | grep -q "1 row"; then
    echo "DB is ready"
    break
  fi
  sleep 3
done

echo ""
echo "=== Current report actions in DB ==="
docker exec $DB_CONTAINER psql -U odoo -d "$DB_NAME" -c "SELECT id, name, report_name, report_file FROM ir_act_report_xml WHERE name IN ('Partner Ledger Report', 'Fees Structure Balance PDF');"

echo ""
echo "=== Force upgrade module ==="
docker exec -u odoo $CONTAINER odoo -u havano_schools_odoo -d $DB_NAME -c /etc/odoo/odoo.conf --db_host=db --db_user=odoo --db_password=odoo --stop-after-init --http-port=8070 2>&1 | tail -30

echo ""
echo "=== Check templates are now in DB ==="
docker exec $DB_CONTAINER psql -U odoo -d "$DB_NAME" -c "SELECT name, key FROM ir_ui_view WHERE key LIKE '%custom_student_statement%' OR key LIKE '%custom_fees_structure_balance%';"

echo ""
echo "=== Check report actions after upgrade ==="
docker exec $DB_CONTAINER psql -U odoo -d "$DB_NAME" -c "SELECT id, name, report_name FROM ir_act_report_xml WHERE name IN ('Partner Ledger Report', 'Fees Structure Balance PDF');"

echo ""
echo "=== Restarting container ==="
docker restart $CONTAINER
echo "Done"
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=180)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:2000])
client.close()
