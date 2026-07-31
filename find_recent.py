import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

cmd = 'find /home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/whatsapp_web_chats /home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/whatsapp -type f -mtime -3'
stdin, stdout, stderr = ssh.exec_command(cmd)
print('Recent files:')
print(stdout.read().decode())
print('Errors:')
print(stderr.read().decode())
ssh.close()
