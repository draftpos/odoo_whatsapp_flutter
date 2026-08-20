import paramiko

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"
container = "odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
base_local = r"c:\odoo19\addons\havano_schools_odoo"
base_remote = "/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/havano_schools_odoo"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, username=username, password=password, timeout=15)

sftp = c.open_sftp()

# Upload the fixed XML file
local = base_local + r"\static\src\xml\havano_partner_ledger_view.xml"
remote = base_remote + "/static/src/xml/havano_partner_ledger_view.xml"
print(f"Uploading {local}")
sftp.put(local, remote)
sftp.close()
print("Upload done!")

# Restart Odoo (static assets need a restart to clear cache)
print("Restarting Odoo...")
i, o, e = c.exec_command(f"docker restart {container}", timeout=60)
print(o.read().decode().strip())
print("Done!")
c.close()
