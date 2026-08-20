import paramiko

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

cmd = """
CONTAINER="odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
DB_CONTAINER="psql_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
DB_NAME="demo1_havano_pro"
BASE="/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/havano_schools_odoo"

echo "=== Checking if new files exist on server ==="
ls -la $BASE/report/custom_student_statement_report.xml 2>&1
ls -la $BASE/report/custom_fees_structure_balance_report.xml 2>&1

echo ""
echo "=== Report actions in DB (report_name and report_file columns) ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT name, report_name, report_file FROM ir_act_report_xml WHERE name IN ('Partner Ledger Report', 'Fees Structure Balance PDF');" 2>&1

echo ""
echo "=== ir_ui_view records for our custom templates ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT name, key FROM ir_ui_view WHERE key LIKE '%custom%' OR key LIKE '%student_statement%' OR key LIKE '%fees_structure_balance%';" 2>&1

echo ""
echo "=== Last 40 lines of Odoo container log ==="
docker logs $CONTAINER --tail 40 2>&1
"""

stdin, stdout, stderr = client.exec_command(cmd)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err)
client.close()
