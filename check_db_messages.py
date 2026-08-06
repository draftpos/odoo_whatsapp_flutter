import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

cmd = "docker exec odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke bash -c \"PGPASSWORD=odoo psql -U odoo -h psql_demo1_havano_pro_pknuzuhckrvwadhoboithcke -d demo1_havano_pro_pknuzuhckrvwadhoboithcke -c 'SELECT id, model, res_id, body, date FROM mail_message ORDER BY id DESC LIMIT 10;'\""
stdin, stdout, stderr = ssh.exec_command(cmd)
print("LATEST MESSAGES:")
print(stdout.read().decode('utf-8'))
print(stderr.read().decode('utf-8'))

ssh.close()
