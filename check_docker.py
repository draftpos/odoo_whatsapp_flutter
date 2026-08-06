import os
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

stdin, stdout, stderr = ssh.exec_command('docker ps -a')
print("STDOUT:")
print(stdout.read().decode('utf-8'))
print("STDERR:")
print(stderr.read().decode('utf-8'))

# Restart db if it's down
stdin, stdout, stderr = ssh.exec_command('docker restart db')
print("Restarting DB:")
print(stdout.read().decode('utf-8'))

ssh.close()
