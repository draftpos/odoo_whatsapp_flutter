import paramiko

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

# Find the correct column name in ir_ui_view
cmd = r"""
DB_CONTAINER="psql_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
DB_NAME="demo1_havano_pro_pknuzuhckrvwadhoboithcke"

echo "=== Columns in ir_ui_view ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "\d ir_ui_view" 2>&1 | head -30

echo ""
echo "=== Columns in ir_act_report_xml ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "\d ir_act_report_xml" 2>&1 | head -30
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:1000])
client.close()
