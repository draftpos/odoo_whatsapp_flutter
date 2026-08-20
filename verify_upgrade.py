import paramiko

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

cmd = r"""
DB_CONTAINER="psql_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
DB_NAME="demo1_havano_pro_pknuzuhckrvwadhoboithcke"

echo "=== Custom templates in ir_ui_view ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT name, key FROM ir_ui_view WHERE key LIKE '%custom_student%' OR key LIKE '%custom_fees%';"

echo ""
echo "=== ALL templates from havano_schools_odoo ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT name, key FROM ir_ui_view WHERE key LIKE '%havano_schools_odoo%' AND key NOT LIKE '%view%' ORDER BY key;"

echo ""
echo "=== Report actions - current report_name ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT name, report_name FROM ir_act_report_xml WHERE report_name LIKE '%partner_ledger%' OR report_name LIKE '%fees_structure%';"

echo ""
echo "=== Odoo log - last 20 lines after restart ==="
CONTAINER="odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
sleep 5
docker logs $CONTAINER --tail 20 2>&1
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:2000])
client.close()
