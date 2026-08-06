import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

# The python code to execute in Odoo shell
ODOO_SHELL_CMD = """
env = self.env
templates = env['whatsapp.template'].search([('body', 'like', '%{{1}}%')])
for tmpl in templates:
    print(f"ID {tmpl.id} '{tmpl.name}':")
    print(tmpl.body)
    print("---")
"""

sftp = ssh.open_sftp()
with sftp.open('/tmp/read_templates.py', 'w') as f:
    f.write(ODOO_SHELL_CMD)
sftp.close()

CONTAINER = 'odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke'
DB_NAME = 'demo1_havano_pro_pknuzuhckrvwadhoboithcke'

cmd = f'docker exec -i {CONTAINER} /entrypoint.sh odoo shell -c /etc/odoo/odoo.conf -d {DB_NAME} < /tmp/read_templates.py'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

ssh.close()
