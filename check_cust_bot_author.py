import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***')

query = """
SELECT m.id, m.author_id, p.name as author_name, m.body
FROM mail_message m
LEFT JOIN res_partner p ON m.author_id = p.id
WHERE m.model = 'discuss.channel' AND m.body LIKE '%Accounting System%'
ORDER BY m.id DESC LIMIT 5;
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
