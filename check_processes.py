import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***')

print("Checking processes...")
stdin, stdout, stderr = ssh.exec_command('ps aux | grep odoo')
print("STDOUT:", stdout.read().decode(errors='ignore'))
ssh.close()
