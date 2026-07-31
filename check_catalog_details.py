import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

ODOO_SHELL_CMD = """
env = self.env
products = env['product.template'].search([('show_in_catalogue', '=', True)])
print(f"Total show_in_catalogue=True: {len(products)}")
for p in products:
    print(f"ID {p.id}: {p.name}, sale_ok={p.sale_ok}, active={p.active}")
"""

sftp = ssh.open_sftp()
with sftp.open('/tmp/check_catalog_details.py', 'w') as f:
    f.write(ODOO_SHELL_CMD)
sftp.close()

cmd = 'docker exec -i odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke /entrypoint.sh odoo shell -c /etc/odoo/odoo.conf -d demo1_havano_pro_pknuzuhckrvwadhoboithcke < /tmp/check_catalog_details.py'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
