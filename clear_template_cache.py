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
CONTAINER="odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"

echo "=== Clearing arch_db cache for both templates (force re-read from arch_fs) ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "UPDATE ir_ui_view SET arch_db = NULL, arch_updated = TRUE WHERE key IN ('havano_schools_odoo.partner_ledger', 'havano_schools_odoo.report_fees_structure_balance');"

echo ""
echo "=== Verifying arch_db is now NULL ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT id, name, key, arch_db IS NULL as arch_cleared FROM ir_ui_view WHERE key IN ('havano_schools_odoo.partner_ledger', 'havano_schools_odoo.report_fees_structure_balance');"

echo ""
echo "=== Restarting Odoo container to reload templates ==="
docker restart $CONTAINER
echo "Done - Odoo will re-read templates from filesystem on next request"
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:1000])
client.close()
