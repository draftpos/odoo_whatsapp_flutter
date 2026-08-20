import paramiko
import json
import re

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

# Upload the updated template file
sftp = client.open_sftp()
base_local = r"c:\odoo19\addons\havano_schools_odoo"
base_remote = "/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/havano_schools_odoo"

print("Uploading havano_partner_ledger_templates.xml...")
sftp.put(
    base_local + r"\views\havano_partner_ledger_templates.xml",
    base_remote + "/views/havano_partner_ledger_templates.xml"
)
print("Upload done!")

# Read the updated file content 
with sftp.open(base_remote + "/views/havano_partner_ledger_templates.xml", "r") as f:
    pl_content = f.read().decode("utf-8")

sftp.close()

# Extract template body
def extract_template_body(xml_content, template_id):
    pattern = rf'<template[^>]*id="{re.escape(template_id)}"[^>]*>(.*?)</template>'
    match = re.search(pattern, xml_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

pl_body = extract_template_body(pl_content, "partner_ledger")
print(f"partner_ledger body: {len(pl_body) if pl_body else 'NOT FOUND'} chars")

if not pl_body:
    print("ERROR: Could not extract template body!")
    client.close()
    exit(1)

# Build arch_db JSON
inner_xml = f'<t t-name="havano_schools_odoo.partner_ledger">\n{pl_body}\n</t>'
pl_arch_db = json.dumps({"en_US": inner_xml})
print(f"arch_db size: {len(pl_arch_db)} chars")

# Write to temp file and copy to DB container
sftp = client.open_sftp()
with sftp.open("/tmp/pl_arch_db.json", "w") as f:
    f.write(pl_arch_db)
sftp.close()

db_container = "psql_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
db_name = "demo1_havano_pro_pknuzuhckrvwadhoboithcke"

cmd = f"""
docker cp /tmp/pl_arch_db.json {db_container}:/tmp/pl_arch_db.json
echo "Copied!"

echo "=== Updating partner_ledger arch_db in DB ==="
docker exec {db_container} psql -U odoo -d {db_name} -c "UPDATE ir_ui_view SET arch_db = (SELECT pg_read_file('/tmp/pl_arch_db.json'))::jsonb, arch_updated = FALSE WHERE key = 'havano_schools_odoo.partner_ledger';"

echo ""
echo "=== Verifying ==="
docker exec {db_container} psql -U odoo -d {db_name} -c "SELECT key, arch_db IS NULL as is_null, length(arch_db::text) as size FROM ir_ui_view WHERE key = 'havano_schools_odoo.partner_ledger';"

echo ""
echo "=== Restarting Odoo ==="
docker restart odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke
echo "Done!"
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err[:2000])
client.close()
