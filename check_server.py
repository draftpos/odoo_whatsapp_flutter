import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

stdin, stdout, stderr = ssh.exec_command('df -h')
print("DISK:")
print(stdout.read().decode('utf-8'))

stdin, stdout, stderr = ssh.exec_command('free -m')
print("MEMORY:")
print(stdout.read().decode('utf-8'))

stdin, stdout, stderr = ssh.exec_command('docker logs --tail 50 db')
print("DB LOGS:")
print(stdout.read().decode('utf-8'))
print(stderr.read().decode('utf-8'))

ssh.close()
