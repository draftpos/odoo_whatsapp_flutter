import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***')

# Execute odoo update command
cmd = "docker exec -i odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke odoo -c /etc/odoo/odoo.conf -u whatsapp_web_chats -d demo1_havano_pro --stop-after-init --db_host db --db_user odoo --db_password odoo"
print(f"Running: {cmd}")
stdin, stdout, stderr = ssh.exec_command(cmd)

print("STDOUT:")
for line in stdout:
    print(line, end="")

print("STDERR:")
for line in stderr:
    print(line, end="")

ssh.close()
