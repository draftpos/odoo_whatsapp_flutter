import paramiko
import json
import re

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

# Read the actual template files from the server
sftp = client.open_sftp()

base = "/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/havano_schools_odoo"

# Read partner_ledger template
with sftp.open(f"{base}/views/havano_partner_ledger_templates.xml", "r") as f:
    pl_content = f.read().decode("utf-8")

# Read fees structure balance template
with sftp.open(f"{base}/report/fees_structure_balance_report_template.xml", "r") as f:
    fsb_content = f.read().decode("utf-8")

sftp.close()

def extract_template_body(xml_content, template_id):
    """Extract the inner content of <template id="..."> and convert to <t t-name="...">"""
    # Find the <template id="..."> tag and extract everything inside it
    # Match <template id="partner_ledger"> ... </template>
    pattern = rf'<template[^>]*id="{re.escape(template_id)}"[^>]*>(.*?)</template>'
    match = re.search(pattern, xml_content, re.DOTALL)
    if match:
        inner = match.group(1).strip()
        # Wrap as Odoo stores it: <t t-name="module.template_id">...</t>
        return inner
    return None

# Extract template bodies
pl_body = extract_template_body(pl_content, "partner_ledger")
fsb_body = extract_template_body(fsb_content, "report_fees_structure_balance")

print(f"partner_ledger body found: {len(pl_body) if pl_body else 'NOT FOUND'} chars")
print(f"report_fees_structure_balance body found: {len(fsb_body) if fsb_body else 'NOT FOUND'} chars")

if not pl_body or not fsb_body:
    print("ERROR: Could not extract template bodies!")
    client.close()
    exit(1)

# Construct the arch_db JSON value - Odoo stores as {"en_US": "<t t-name=\"...\">...</t>"}
def make_arch_db(module, template_id, body):
    inner_xml = f'<t t-name="{module}.{template_id}">\n{body}\n</t>'
    return json.dumps({"en_US": inner_xml})

pl_arch_db = make_arch_db("havano_schools_odoo", "partner_ledger", pl_body)
fsb_arch_db = make_arch_db("havano_schools_odoo", "report_fees_structure_balance", fsb_body)

print(f"\npl_arch_db size: {len(pl_arch_db)} chars")
print(f"fsb_arch_db size: {len(fsb_arch_db)} chars")

# Write the arch_db JSON to temp files on server and apply via psql
sftp = client.open_sftp()
with sftp.open("/tmp/pl_arch_db.json", "w") as f:
    f.write(pl_arch_db)
with sftp.open("/tmp/fsb_arch_db.json", "w") as f:
    f.write(fsb_arch_db)
sftp.close()

# Now update via psql - using \lo_import or stdin
# Use a psql approach via docker exec with heredoc
db_container = "psql_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
db_name = "demo1_havano_pro_pknuzuhckrvwadhoboithcke"

# Copy temp files into db container
cmd_copy = f"""
docker cp /tmp/pl_arch_db.json {db_container}:/tmp/pl_arch_db.json
docker cp /tmp/fsb_arch_db.json {db_container}:/tmp/fsb_arch_db.json
echo "Files copied to DB container"
"""
stdin, stdout, stderr = client.exec_command(cmd_copy, timeout=15)
print(stdout.read().decode())

# Use psql to update with file content
cmd_update = f"""
DB_CONTAINER="{db_container}"
DB_NAME="{db_name}"

echo "=== Updating partner_ledger arch_db ==="
PL_JSON=$(cat /tmp/pl_arch_db.json)
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "UPDATE ir_ui_view SET arch_db = '${{PL_JSON//\\'/\\'\\'}}', arch_updated = FALSE WHERE key = 'havano_schools_odoo.partner_ledger';"

echo "=== Updating report_fees_structure_balance arch_db ==="
FSB_JSON=$(cat /tmp/fsb_arch_db.json)
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "UPDATE ir_ui_view SET arch_db = '${{FSB_JSON//\\'/\\'\\'}}', arch_updated = FALSE WHERE key = 'havano_schools_odoo.report_fees_structure_balance';"

echo "=== Verifying ==="
docker exec $DB_CONTAINER psql -U odoo -d $DB_NAME -c "SELECT key, arch_db IS NULL as is_null, length(arch_db::text) as size FROM ir_ui_view WHERE key IN ('havano_schools_odoo.partner_ledger', 'havano_schools_odoo.report_fees_structure_balance');"
"""

stdin, stdout, stderr = client.exec_command(cmd_update, timeout=30)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:2000])

# Restart container
cmd_restart = """
docker restart odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke
echo "Restarted!"
"""
stdin, stdout, stderr = client.exec_command(cmd_restart, timeout=30)
print(stdout.read().decode())

client.close()
