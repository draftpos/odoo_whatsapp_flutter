import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***')
stdin, stdout, stderr = ssh.exec_command('cat /home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/whatsapp_web_chats/models/mail_message.py')
print(stdout.read().decode())
ssh.close()
