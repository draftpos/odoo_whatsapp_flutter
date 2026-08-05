import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***')

# Fix existing live messages that were copied wrong
query = """
UPDATE mail_message AS m1
SET author_id = CASE
    WHEN wm.message_type = 'inbound' THEN NULL
    WHEN wm.message_type = 'outbound' THEN (SELECT res_id FROM ir_model_data WHERE module = 'base' AND name = 'partner_root' LIMIT 1)
    ELSE m1.author_id
END
FROM whatsapp_message wm, mail_message m2
WHERE m1.model = 'discuss.channel' 
  AND m1.message_type = 'whatsapp_message'
  AND m2.id = wm.mail_message_id
  AND m1.body = m2.body
  AND abs(extract(epoch from (m1.create_date - m2.create_date))) < 10;
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
