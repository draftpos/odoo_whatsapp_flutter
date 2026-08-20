import paramiko

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

# Read the actual XML content from the uploaded files on the server
# and update the DB directly
cmd = r"""
DB_CONTAINER="psql_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
DB_NAME="demo1_havano_pro_pknuzuhckrvwadhoboithcke"
BASE="/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/havano_schools_odoo"

echo "=== Reading partner_ledger template from file ==="
cat "$BASE/views/havano_partner_ledger_templates.xml" | head -5

echo ""
echo "=== Checking template arch currently in DB for partner_ledger ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT id, name, key, length(arch) as arch_length FROM ir_ui_view WHERE key = 'havano_schools_odoo.partner_ledger';"

echo ""
echo "=== Checking template arch currently in DB for report_fees_structure_balance ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT id, name, key, length(arch) as arch_length FROM ir_ui_view WHERE key = 'havano_schools_odoo.report_fees_structure_balance';"
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:1000])
client.close()
