import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***')

print("Restarting docker container...")
stdin, stdout, stderr = ssh.exec_command('docker restart odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke')
print("STDOUT:", stdout.read().decode(errors='ignore'))
print("STDERR:", stderr.read().decode(errors='ignore'))
ssh.close()
