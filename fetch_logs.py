import paramiko

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, timeout=15)

container = "odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"

# Check the full traceback from /var/log/odoo/odoo.log to get the REAL cause
stdin, stdout, stderr = client.exec_command(
    f"docker exec {container} grep -n -A 5 -B 2 'financial_report_override\\|circular import\\|ImportError\\|Couldn.*load.*havano' /var/log/odoo/odoo.log | tail -60",
    timeout=20
)
print("=== Full error context from odoo.log ===")
print(stdout.read().decode())

# Also check what's actually on the remote __init__.py to confirm our upload succeeded
stdin, stdout, stderr = client.exec_command(
    f"docker exec {container} cat /mnt/extra-addons/havano_schools_odoo/models/__init__.py",
    timeout=15
)
print("\n=== Remote __init__.py ===")
print(stdout.read().decode())

client.close()
