import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='Farai@#')
stdin, stdout, stderr = ssh.exec_command('docker exec odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke env')
print(stdout.read().decode())
ssh.close()
