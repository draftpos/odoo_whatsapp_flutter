import os
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password=os.environ.get('SERVER_PASSWORD'))
query = "SELECT m1.id, m1.body, m1.author_id, wm.message_type, wm.is_bot_message FROM mail_message m1 JOIN whatsapp_message wm ON m1.body = (SELECT body FROM mail_message m2 WHERE m2.id = wm.mail_message_id) WHERE m1.model = 'discuss.channel' ORDER BY m1.id DESC LIMIT 5;"
cmd = f"docker exec -i -e PGPASSWORD=odoo odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke psql -h db -U odoo -d demo1_havano_pro_pknuzuhckrvwadhoboithcke -c \"{query}\""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
