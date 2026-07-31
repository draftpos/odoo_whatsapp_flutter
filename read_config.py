import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

cmd = 'cat /home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/config/odoo.conf'
print('Reading odoo.conf:')
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
