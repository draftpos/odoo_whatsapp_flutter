import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***')

stdin, stdout, stderr = ssh.exec_command("docker logs --tail 200 odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke")
print("DOCKER LOGS STDERR:\n", stderr.read().decode(errors="ignore"))
print("DOCKER LOGS STDOUT:\n", stdout.read().decode(errors="ignore"))
ssh.close()
