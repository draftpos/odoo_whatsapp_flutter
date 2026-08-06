import os
import paramiko
import re

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

ODOO_SHELL_CMD = """
import re
env = self.env
# Find all templates that contain {{1}}
templates = env['whatsapp.template'].search([('body', 'like', '%{{1}}%')])
count = 0
for tmpl in templates:
    old_body = tmpl.body or ''
    # Remove {{1}} and "Hi {{1}}," if it exists
    new_body = old_body.replace('Hi {{1}},\\n\\n', 'Hi,\\n\\n')
    new_body = new_body.replace('Hi {{1}}, ', 'Hi, ')
    new_body = new_body.replace('Hi {{1}}\\n', 'Hi\\n')
    new_body = new_body.replace('{{1}}', '')
    
    # Re-number remaining variables: {{2}} -> {{1}}, {{3}} -> {{2}}, etc.
    # We do this from {{2}} up to {{99}}
    for i in range(2, 20):
        old_var = f'{{{{{i}}}}}'
        new_var = f'{{{{{i-1}}}}}'
        new_body = new_body.replace(old_var, new_var)
        
    # Also delete associated variable records for the body to prevent leftover garbage
    # Odoo typically recreates them or expects them to be cleared.
    tmpl.write({'body': new_body})
    count += 1
    print(f"Updated live template ID {tmpl.id}: '{tmpl.name}'")

print(f"Total live templates fully updated: {count}")
env.cr.commit()
"""

sftp = ssh.open_sftp()
with sftp.open('/tmp/update_templates3.py', 'w') as f:
    f.write(ODOO_SHELL_CMD)
sftp.close()

CONTAINER = 'odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke'
DB_NAME = 'demo1_havano_pro_pknuzuhckrvwadhoboithcke'

cmd = f'docker exec -i {CONTAINER} /entrypoint.sh odoo shell -c /etc/odoo/odoo.conf -d {DB_NAME} < /tmp/update_templates3.py'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("LIVE OUTPUT:")
print(stdout.read().decode('utf-8', errors='replace'))
print("ERRORS:")
print(stderr.read().decode('utf-8', errors='replace'))
ssh.close()
