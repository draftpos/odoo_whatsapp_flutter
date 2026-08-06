import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password=os.environ.get('SERVER_PASSWORD'))

stdin, stdout, stderr = ssh.exec_command('cat /home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/dev_whatsapp_chatbot_ent/models/wa_chatbot_processor.py')
print(stdout.read().decode(errors='ignore'))
ssh.close()
