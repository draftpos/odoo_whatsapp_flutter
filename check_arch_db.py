import paramiko
import json

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

# Read the template XML files from the server and push to DB directly
cmd = r"""
DB_CONTAINER="psql_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
DB_NAME="demo1_havano_pro_pknuzuhckrvwadhoboithcke"
BASE="/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/havano_schools_odoo"

echo "=== Current arch_fs for partner_ledger ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT id, name, key, arch_fs FROM ir_ui_view WHERE key = 'havano_schools_odoo.partner_ledger';"

echo ""
echo "=== Current arch_fs for report_fees_structure_balance ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT id, name, key, arch_fs FROM ir_ui_view WHERE key = 'havano_schools_odoo.report_fees_structure_balance';"

echo ""
echo "=== arch_db for partner_ledger (first 200 chars) ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT id, left(arch_db::text, 200) FROM ir_ui_view WHERE key = 'havano_schools_odoo.partner_ledger';"

echo ""
echo "=== arch_db for fees structure balance (first 200 chars) ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT id, left(arch_db::text, 200) FROM ir_ui_view WHERE key = 'havano_schools_odoo.report_fees_structure_balance';"
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:1000])
client.close()
