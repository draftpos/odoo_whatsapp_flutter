import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***')

# Query to find recent discuss.channel messages
query = """
SELECT id, model, res_id, author_id, message_type, body, create_date 
FROM mail_message 
WHERE model = 'discuss.channel' AND body LIKE '%Welcome to Havano!%'
ORDER BY id DESC LIMIT 5;
"""

cmd = f"docker exec -i -e PGPASSWORD=odoo odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke psql -h db -U odoo -d demo1_havano_pro -c \"{query}\""
print(f"Running: {cmd}")
stdin, stdout, stderr = ssh.exec_command(cmd)

print("STDOUT:")
for line in stdout:
    print(line, end="")

print("STDERR:")
for line in stderr:
    print(line, end="")

ssh.close()
