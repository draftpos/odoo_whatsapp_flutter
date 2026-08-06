import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

stdin, stdout, stderr = ssh.exec_command('docker ps')
print("DOCKER PS:")
print(stdout.read().decode('utf-8'))

ssh.close()
