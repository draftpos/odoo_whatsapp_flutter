import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***')

query = """
SELECT id, mail_message_id, message_type, is_bot_message
FROM whatsapp_message
WHERE mail_message_id IN (2212, 2210, 2053, 2200, 2195, 2214) OR id > 0
ORDER BY id DESC LIMIT 10;
"""

cmd = f"docker exec -i -e PGPASSWORD=odoo odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke psql -h db -U odoo -d demo1_havano_pro_pknuzuhckrvwadhoboithcke -c \"{query}\""
print(f"Running: {cmd}")
stdin, stdout, stderr = ssh.exec_command(cmd)

print("STDOUT:")
for line in stdout:
    print(line, end="")

print("STDERR:")
for line in stderr:
    print(line, end="")

ssh.close()
