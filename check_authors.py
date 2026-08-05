import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***')

# Query to find recent discuss.channel messages
query = """
SELECT id, model, res_id, author_id, message_type, create_date 
FROM mail_message 
WHERE model = 'discuss.channel' 
ORDER BY id DESC LIMIT 10;
"""

stdin, stdout, stderr = ssh.exec_command(f"docker exec -i odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke psql -h db -U odoo -d demo1_havano_pro -c \"{query}\"")
print("Discuss channel messages:\n", stdout.read().decode(errors="ignore"))
print("STDERR1:\n", stderr.read().decode(errors="ignore"))

ssh.close()
