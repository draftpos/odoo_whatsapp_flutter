import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

ODOO_SHELL_CMD = """
env = self.env
# Only update the 7 templates created recently
templates = env['whatsapp.template'].search([('name', 'ilike', 'Showline Template')])
count = 0
for tmpl in templates:
    if '{{1}}' in tmpl.body:
        new_body = tmpl.body.replace('Hi {{1}}, ', 'Hi, ').replace('{{1}}', '')
        tmpl.write({'body': new_body})
        count += 1
        print(f"Updated live template ID {tmpl.id}: '{tmpl.name}'")

print(f"Total live templates updated: {count}")
env.cr.commit()
"""

sftp = ssh.open_sftp()
with sftp.open('/tmp/update_templates2.py', 'w') as f:
    f.write(ODOO_SHELL_CMD)
sftp.close()

CONTAINER = 'odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke'
DB_NAME = 'demo1_havano_pro_pknuzuhckrvwadhoboithcke'

cmd = f'docker exec -i {CONTAINER} /entrypoint.sh odoo shell -c /etc/odoo/odoo.conf -d {DB_NAME} < /tmp/update_templates2.py'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("LIVE OUTPUT:")
print(stdout.read().decode('utf-8', errors='replace'))
ssh.close()
