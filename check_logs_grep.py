import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***')

stdin, stdout, stderr = ssh.exec_command("docker logs odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke 2>&1 | grep 'Failed to mirror'")
print("DOCKER LOGS GREP:\n", stdout.read().decode(errors="ignore"))
ssh.close()
