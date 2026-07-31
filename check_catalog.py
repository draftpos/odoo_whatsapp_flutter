import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

ODOO_SHELL_CMD = """
count = self.env['product.template'].search_count([('show_in_catalogue', '=', True)])
print(f"Products in Odoo catalogue: {count}")
"""

sftp = ssh.open_sftp()
with sftp.open('/tmp/check_catalog.py', 'w') as f:
    f.write(ODOO_SHELL_CMD)
sftp.close()

cmd = 'docker exec -i odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke /entrypoint.sh odoo shell -c /etc/odoo/odoo.conf -d demo1_havano_pro_pknuzuhckrvwadhoboithcke < /tmp/check_catalog.py'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
