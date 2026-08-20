import paramiko
import sys

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

# Upload the updated files
sftp = client.open_sftp()
base_local = r"c:\odoo19\addons\havano_schools_odoo"
base_remote = "/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/havano_schools_odoo"

files_to_upload = [
    (r"\models\__init__.py", "/models/__init__.py"),
    (r"\models\havano_admin_comment.py", "/models/havano_admin_comment.py"),
    (r"\models\havano_partner_ledger.py", "/models/havano_partner_ledger.py"),
    (r"\models\res_company.py", "/models/res_company.py"),
    (r"\models\res_config_settings.py", "/models/res_config_settings.py"),
    (r"\models\daily_register.py", "/models/daily_register.py"),
    (r"\views\res_config_settings_views.xml", "/views/res_config_settings_views.xml"),
    (r"\views\havano_partner_ledger_templates.xml", "/views/havano_partner_ledger_templates.xml"),
    (r"\views\school_fees_structure_views.xml", "/views/school_fees_structure_views.xml"),
    (r"\static\src\xml\havano_partner_ledger_view.xml", "/static/src/xml/havano_partner_ledger_view.xml"),
    (r"\static\src\js\havano_partner_ledger.js", "/static/src/js/havano_partner_ledger.js")
]

try:
    for local_path, remote_path in files_to_upload:
        print(f"Uploading {local_path}...")
        sftp.put(base_local + local_path, base_remote + remote_path)
    print("Uploads done!")
except Exception as e:
    print("Error uploading files:", e)
finally:
    sftp.close()

# Update module in Odoo
odoo_container = "odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"

cmd = f"""
echo "=== Upgrading havano_schools_odoo ==="
docker exec {odoo_container} odoo -u havano_schools_odoo -d $(docker exec {odoo_container} bash -c "grep \"^db_name\" /etc/odoo/odoo.conf | cut -d= -f2 | tr -d ' '") --stop-after-init
echo "=== Restarting Odoo ==="
docker restart {odoo_container}
echo "Done!"
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print("STDERR:", err)

client.close()
