import os
import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password=os.environ.get('SERVER_PASSWORD'))
query = "SELECT res_id FROM ir_model_data WHERE module = 'base' AND name = 'partner_root';"
cmd = f"docker exec -i -e PGPASSWORD=odoo odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke psql -h db -U odoo -d demo1_havano_pro_pknuzuhckrvwadhoboithcke -c \"{query}\""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
