import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

ODOO_SHELL_CMD = """
try:
    res = self.env["product.product"].search_read([("show_in_catalogue", "=", True)])
    print("SUCCESS:", len(res))
except Exception as e:
    print("ERROR:", e)
"""

sftp = ssh.open_sftp()
with sftp.open('/tmp/check_pp.py', 'w') as f:
    f.write(ODOO_SHELL_CMD)
sftp.close()

cmd = 'docker exec -i odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke /entrypoint.sh odoo shell -c /etc/odoo/odoo.conf -d demo1_havano_pro_pknuzuhckrvwadhoboithcke < /tmp/check_pp.py'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
