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

try:
    print("Uploading havano_partner_ledger.py...")
    sftp.put(
        base_local + r"\models\havano_partner_ledger.py",
        base_remote + "/models/havano_partner_ledger.py"
    )

    print("Uploading havano_partner_ledger_view.xml...")
    sftp.put(
        base_local + r"\static\src\xml\havano_partner_ledger_view.xml",
        base_remote + "/static/src/xml/havano_partner_ledger_view.xml"
    )
    print("Uploads done!")
except Exception as e:
    print("Error uploading files:", e)
finally:
    sftp.close()

# Restart Odoo to apply Python changes and flush any backend caches
cmd = "docker restart odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
out = stdout.read().decode()
err = stderr.read().decode()
print("Odoo Restarted:", out)
if err:
    print("STDERR:", err)

client.close()
